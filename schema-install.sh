#!/bin/sh

# NB: unmodified MESON_BUILD_ROOT point to the top directory(?)
cp "${MESON_SOURCE_ROOT}/uk.co.archaicgroves.backuper.gschema.xml" "/usr/share/glib-2.0/schemas/"
glib-compile-schemas "/usr/share/glib-2.0/schemas/"
