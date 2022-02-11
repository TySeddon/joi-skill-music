from turtle import pd
import pandas as pd

def chunk(lst, n):
    for i in range(0,len(lst), n):
        yield lst[i:i+n]

history = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
movement_percent = sum(history)/len(history)
print(f"{movement_percent}%")

chunks = chunk(history, 5)
periods = []
for c in chunks:
    pct = sum(c)/len(c)
    periods.append(pct)

print(periods)    

# rolling 
s = pd.Series(history)
window_size = 5
print(s.rolling(window_size).sum().apply(lambda o: o/window_size).tolist())
