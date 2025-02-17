#!/bin/bash
# git remote add iowarp https://github.com/iowarp/iowarp-runtime-util.git
# git remote add grc https://github.com/grc-iit/chimaera-util.git
gh pr create --title $1 --body "" --repo=grc-iit/chimaera-util
gh pr create --title $1 --body "" --repo=iowarp/iowarp-runtime-util
