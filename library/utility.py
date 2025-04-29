from time import localtime, mktime
import re

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
            if d == 'timestamp': #Ajan formatointi h:m, lisää nollia minuutteihin
                  time = localtime(data[d])
                  time = f'{time[3]}:{'{:0>{w}}'.format(str(time[4]), w=2)}'
                  formatted.insert(0, f'TIME: {time}')
            elif d != 'id': #Print all but id
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

def parse_kubios_message(data: dict) -> dict:
      stamp = mktime(localtime())
      data = data['data']['analysis']
      data = {
                  "id": stamp,
                  "timestamp": stamp,
                  "mean_hr": round(data['mean_hr_bpm']),
                  "mean_ppi": round(data['mean_rr_ms']),
                  "rmssd": round(data['rmssd_ms']),
                  "sdnn": round(data['sdnn_ms']),
                  "sns": f'{data["sns_index"]:.2f}',
                  "pns": f'{data["pns_index"]:.2f}',
                  "phys_age": data['physiological_age']
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


#*TODO* Read parameters wifi params from a txt file using regex
def read_wifi_file() -> tuple:
      with open('/settings.txt') as file:
            pass
             
