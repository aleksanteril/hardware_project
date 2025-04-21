from time import localtime

def format_filenames(files: list) -> list:
      formatted = []
      for name in files:
            name = name.split('_')
            date = localtime(int(name[1]))
            name = f'{name[0].upper()} {date[2]}/{date[1]}/{date[0]}'
            formatted.append(name)
      return formatted


def format_data(data: dict) -> list:
      formatted = []
      for d in data:
            formatted.append(f'{d.upper()}: {data[d]}')
      return formatted
