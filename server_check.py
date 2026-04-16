for A in range(100):
  b=1
  for x in range(1000):
    for y in range(1000):
      b=b*(((x+2*y)!=58) or (((A-x)>0)==((A+y)>0)))
  if b==1:
    print(A)