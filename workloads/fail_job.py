import sys 

print("Starting failure test")

print("Something went wrong", file=sys.stderr)

sys.exit(1)

