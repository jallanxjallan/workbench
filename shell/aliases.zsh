# Lightweight aliases only (no logic)


alias ll='ls -alF'
alias gs='git status'
alias gd='git diff'
alias srczh='source ~/.zshrc'
if [[ -n "${WORKBENCH_ROOT:-}" && -x "${WORKBENCH_ROOT}/bin/wkb" ]]; then
  alias wkb='${WORKBENCH_ROOT}/bin/wkb'
fi


alias ascsmoke='asc dev smoke-test'
alias ascq='asc query'
