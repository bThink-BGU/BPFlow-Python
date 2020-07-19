import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
from sympy import *
from sympy.stats import Normal, E, Expectation, where
from sympy.abc import x


def d2aExpctation(thresholds, levels):
  levels = len(thresholds)
  
  X1 = Normal('X1', 0, 1)
  X2 = Normal('X2', 0, 1)

  print(E(X1 + X2, X1 < 10).simplify() )
 
  print("thresholds=", thresholds)
  arr = [(i, x <= thresholds[i]) for i in range(levels)] + [(levels, True)]
  a2d = Lambda(x, Piecewise(*arr))
  
  print(a2d)
  for i in range(2 * levels - 1):
    print(i, "-->")
    if i==0:
      print("\t", E(X1 + X2, And(Le(X1,thresholds[0]), Le(X2, thresholds[0]))).evalf(2))
    elif i==1:
      print("\t", E(X1 + X2, (X1 < thresholds[0] and X2 < thresholds[1] and X2 > thresholds[0]) or (X2 < thresholds[0] and X1 < thresholds[1] and X1 > thresholds[0])).evalf(2))
    else:
      print("\t", E(X1 + X2, Eq(a2d(X1) + a2d(X2), i)).evalf(2))

    
d2aExpctation([-1.1, 0, 1.1], 0)