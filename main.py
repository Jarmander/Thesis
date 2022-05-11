import os
import csv
from DemofileParse import parse_demofile
from pathlib import Path

DEM_FILE_PATH = Path(r'C:\Users\kalha\PycharmProjects\Thesis\files')
CSV_FILE_PATH = Path(r'C:\Users\kalha\PycharmProjects\Thesis\files\data.csv')


def list_demofiles(path: Path) -> list:
    l = []
    for filename in os.listdir(path):
        if filename.endswith('.dem'):
            l.append(path / filename)
    return l


def check_csv(demo_paths: iter, csv_path: Path | str) -> list:

    if not os.path.exists(csv_path):
        return list(demo_paths)

    l = []
    with open(csv_path, mode='r', newline='') as csvfile:
        csvfile = csvfile.readlines()

    data = csv.DictReader(csvfile, quoting=csv.QUOTE_NONE)
    matches = (match['matchID'] for match in data)

    for path in demo_paths:
        if path.stem not in matches:
            l.append(path)

    return l


def write_data_to_csv(data: str, csv_path: Path | str):

    file_exists = os.path.exists(csv_path)

    with open(csv_path, mode='a+', newline='') as csvfile:
        writer = csv.writer(csvfile)
        csv_rows = data.replace('"', '').split('\r\n')
        if file_exists:
            csv_rows.pop(0)
        for row in csv_rows:
            writer.writerow([row])


if __name__ == '__main__':
    demo_list = list_demofiles(DEM_FILE_PATH)
    print(f'{len(demo_list)} demo files found, comparing to processed files in csv...')

    if demo_list:

        demos_to_process = check_csv(demo_list, CSV_FILE_PATH)
        demos_num = len(demos_to_process)
        print(f'{demos_num} files to process, commencing...')

        error_num = 0
        processed_num = 0

        for demo_path in demos_to_process:

            try:
                data = parse_demofile(demo_path)
                write_data_to_csv(data, CSV_FILE_PATH)
                print(f'{demo_path.stem} processed')
                processed_num += 1

            except Exception as e:
                print(e)
                error_num += 1

        print(f'Demofiles to be processed: {demos_num}   Succesfully processed: {processed_num}    Errors:{error_num}')

    else:
        print('No demo files found in directory!')
