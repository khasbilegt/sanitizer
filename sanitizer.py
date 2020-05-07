from pathlib import Path
from pprint import pprint
from datetime import datetime
from concurrent.futures.thread import ThreadPoolExecutor

import json
import hashlib
import shutil


class Sanitizer:
    LABELS = {}
    CHECKSUMS = {}
    SANITIZED_CHECKSUMS = {}
    PATHS = {}
    ROOT = Path.cwd().parent
    SOURCE = ROOT / "NUM HW database"
    CLEANED = ROOT / "DATASET"

    @classmethod
    def get_total_count(cls):
        count = 0
        for key, value in cls.CHECKSUMS.items():
            count += len(value)
        return count

    @classmethod
    def get_sanitized_count(cls):
        return len(cls.SANITIZED_CHECKSUMS.values())

    @classmethod
    def read_files(cls):
        with ThreadPoolExecutor() as executor:
            LABELS, CONFIG = executor.map(read, ["labels.json", "config.json"])
            CONFIG = dict(
                ((str(value), key) for key, value in CONFIG["labels"].items())
            )
            cls.LABELS = dict(
                (
                    (label, {"id": CONFIG[symbol], "symbol": symbol})
                    for label, symbol in (
                        (label, item["symbol"])
                        for label, item in LABELS.items()
                        if item["symbol"] in CONFIG
                    )
                )
            )

    @classmethod
    def collect_hash(cls):
        for path in (path for path in cls.SOURCE.iterdir() if path.is_dir()):
            with ThreadPoolExecutor() as executor:
                cls.CHECKSUMS[str(path.stem).split("/")[-1]] = tuple(
                    executor.map(cls.fingerprint, path.iterdir())
                )

    @classmethod
    def ignore_duplicated(cls):
        for label, items in cls.CHECKSUMS.items():
            with ThreadPoolExecutor() as executor:
                result = tuple(executor.map(cls.sanitize, items))
                cls.PATHS[label] = {"items": result, "count": len(result)}

    @classmethod
    def finish_process(cls):
        FINAL = []
        counter = 0
        for key, value in cls.PATHS.items():
            for item in value["items"]:
                if item:
                    FINAL.append(tuple((counter, item)))
                    counter += 1
            counter = 0

        with ThreadPoolExecutor() as executor:
            result = tuple(executor.map(cls.write_files, FINAL))
            print(f"[~] {len(result)} files are saved!")

    @classmethod
    def fingerprint(cls, filename):
        try:
            return (
                cls.LABELS[str(filename.parent.stem).split("/")[-1]]["id"],
                filename,
                hashlib.md5(open(filename, "rb").read()).hexdigest(),
            )
        except KeyError:
            # print(f"[!] Ignored: {str(filename.parent.stem).split('/')[-1]}")
            pass

    @classmethod
    def sanitize(cls, item):
        if item:
            key, filename, fingerprint = item

            if not fingerprint in cls.SANITIZED_CHECKSUMS.values():
                cls.SANITIZED_CHECKSUMS[filename] = fingerprint

                dest = (
                    Path(cls.CLEANED)
                    / Path(key)
                    / f"{key}_{filename.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                )
                # print(filename, dest)
                return (filename, dest)
            # else:
            #     print(f"[!] Exists: {filename.name} ({fingerprint})")

    @classmethod
    def write_files(cls, item):
        key, (filename, dest) = item
        dest = filename.parent / str(dest).replace(filename.stem, str(key))

        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(filename, dest)
        return dest

    @classmethod
    def run(cls):
        cls.read_files()
        cls.collect_hash()
        cls.ignore_duplicated()
        cls.finish_process()

        print(f"[~] TOTAL    : {cls.get_total_count()}")
        print(f"[~] SANITIZED: {cls.get_sanitized_count()}")


def read(filename):
    if Path(filename).exists():
        with open(filename, "r") as file:
            return json.load(file)
    raise FileNotFoundError


def main():
    Sanitizer.run()


if __name__ == "__main__":
    main()
