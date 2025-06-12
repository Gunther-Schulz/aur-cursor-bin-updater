#!/bin/bash

XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-~/.config}

# Allow users to override command-line options
if [[ -f $XDG_CONFIG_HOME/cursor-flags.conf ]]; then
  CURSOR_USER_FLAGS="$(sed 's/#.*//' $XDG_CONFIG_HOME/cursor-flags.conf | tr '\n' ' ')"
fi

# Run with flags
_app=/usr/share/cursor/resources/app
ELECTRON_RUN_AS_NODE=1 exec /usr/share/cursor/electron ${_app}/out/cli.js "$CURSOR_USER_FLAGS" --app=${_app} "$@"
