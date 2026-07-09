# Native deps beyond the .replit language modules (python-3.12, nodejs-20).
# LightGBM (pulled in by NannyML) and SHAP need libgomp.so.1 / libstdc++.so.6;
# gcc covers any sdist that must compile. scripts/replit_env.sh wires
# LD_LIBRARY_PATH to these at build/start if the dynamic loader misses them.
{ pkgs }: {
  deps = [
    pkgs.gcc                 # C/C++ toolchain for source builds
    pkgs.stdenv.cc.cc.lib    # gcc's lib output: BOTH libstdc++.so.6 AND libgomp.so.1
    pkgs.libgcc              # libgcc_s.so.1 only (harmless extra; NOT libgomp)
    pkgs.glibcLocales
    pkgs.zlib
  ];
}
