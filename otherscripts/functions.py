def read_secret(secretName):
  with open('secrets.txt') as file:
    content = file.read().splitlines()
    for line in content:
      if (line.split('=')[0] == secretName):
        return line.split('=')[1]
