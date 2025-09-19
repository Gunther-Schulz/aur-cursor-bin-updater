#!/bin/bash
_api="https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable"
pkgver=$(curl -Ls "$_api" | grep -oP '"version":"\K[^"]+')
_commit=_commit=$(curl -Ls "$_api" | grep -oP '"commitSha":"\K[^"]+')

if [ $(grep pkgver= PKGBUILD) =  "pkgver=$pkgver" ];then
  echo Already latest
  exit 1
fi

sed \
  -e "s/pkgver=.*/$pkgver/" \
  -e "s/pkgrel=.*/pkgrel=1/" \
  -e "s/_commit=.*/$_commit/" \
  -e "s/_electron=.*/_electron=$(echo electron34)/" \
  -e "s/sha512sums[0]=.*/sha512sums[0]=$(curl https://downloads.cursor.com/production/${_commit}/linux/x64/deb/amd64/deb/cursor_${pkgver}_amd64.deb | sha512sum)/" \
  PKGBUILD #> PKGBUILD
