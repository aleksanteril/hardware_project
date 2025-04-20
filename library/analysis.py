from math import sqrt

'''This file contains all mathematical functions for calculating the HRV parameters locally'''


test_data = [896, 936, 972, 964, 953, 956, 935, 865, 
             847, 704, 677, 864, 955, 980, 957, 967, 
             796, 920, 925, 931, 892, 704, 889, 772, 
             924, 948, 956, 960, 940, 924, 912, 768, 
             864, 873, 603, 884, 817, 813, 943, 940, 
             600, 917, 900, 900, 915, 905, 935, 945, 
             924, 980]


#Calculate diffrences between indexes
def diff(ppi: list) -> list:
      if len(ppi) < 2:
            raise ValueError('Array must be atleast 2 long to calculate diffrences')
      diffs = []
      for i in range(len(ppi)-1):
            diffs.append(ppi[i+1] - ppi[i])
      return diffs


def mean_hr(ppi: list) -> float:
      return 60000 / mean_ppi(ppi)


def mean_ppi(ppi: list) -> float:
      if len(ppi) < 1:
            raise ValueError('Can not calculate mean values from empty list')
      return sum(ppi) / len(ppi)


def rmssd(ppi: list) -> float:
      sum = 0
      diffs = diff(ppi)
      for rr in diffs:
            sum += rr**2
      rmssd = sqrt(sum / (len(ppi)-1))
      return rmssd


def sdnn(ppi: list) -> float:
      sum = 0
      mean_rr = mean_ppi(ppi)
      for rr in ppi:
            sum += (rr - mean_rr)**2
      sdnn = sqrt(sum / (len(ppi)-1))
      return sdnn
