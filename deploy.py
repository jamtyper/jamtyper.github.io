import os

def sh(command):
  print('')
  print(command)
  print('')
  error = os.system(command)
  if error:
    raise RuntimeError(f'Exit code {error}.')

def cd(directory):
  print('')
  print('cd', directory)
  print('')
  os.chdir(directory)

cd('../jamtyper.github.io')
sh('rm -rf *')
sh('cp -R ../jamtyper/* .')
# sh('cp index.html 404.html')
sh('echo "jamtyper.com" > CNAME')
sh('git add -A')
sh('git commit -m "Update."')
sh('git push')
