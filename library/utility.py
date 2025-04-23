from time import localtime, mktime

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
            if d == 'id':
                  continue
            if d == 'timestamp': #Ajan formatointi h:m, lisää nollia minuutteihin
                  data[d] = localtime(data[d])
                  data[d] = f'{data[d][3]}:{'{:0>{w}}'.format(str(data[d][4]), w=2)}'
                  formatted.insert(0, f'TIME: {data[d]}')
            else:
                  formatted.append(f'{d.upper()}: {data[d]}')
      return formatted

def format_kubios_message(ppi: list) -> dict:
            stamp = mktime(localtime())
            data =  {
                        "id": stamp,
                        "type": "RRI",
                        "data": ppi,
                        "analysis": { "type": "readiness" }
                  }
            return data


def calculate_plotting_values(samples: list) -> tuple[int, float]:
      #Calculate scaling factor
      max_list = max(samples)
      min_list = min(samples)
      scale_fc = 42 / (max_list - min_list)
      return max_list, scale_fc


def plot_sample(sample: int, max_list: int, scale_fc: float) -> int:
      pos = (sample - max_list) * scale_fc * -1
      return round(pos)
