import time 
import os 
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir")
args= parser.parse_args()

print("job started")

time.sleep(5)

output_dir_result = os.path.join(args.output_dir,"result.txt")

with open(output_dir_result,"a") as f:
    f.write("something")

print("job finished")

