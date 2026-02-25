# Git helpers

gclean() {
git branch --merged | grep -v '\*\|main\|master' | xargs -r git branch -d
}


glast() {
git log -1 --stat
}