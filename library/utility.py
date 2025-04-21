from time import localtime

def format_filenames(files: list) -> list:
      formatted = []
      for name in files:
            name = name.split('_')
            date = localtime(int(name[1]))
            name = f'{name[0].upper()} {date[2]}_{date[1]}_{date[0]}'
            formatted.append(name)
      return formatted
