# Acceptance Matrix

Use this matrix to decide whether a release candidate satisfies the desktop-app
goal. A release is not ready for normal users until every row has current
evidence in a filled copy of `docs/RELEASE_EVIDENCE_TEMPLATE.md`. Use
`docs/MANUAL_USER_SMOKE.md` to collect the manual user-smoke evidence.

| Requirement | Evidence Needed | Current Gate |
| --- | --- | --- |
| Windows users can download and start without Python or the command line. | `ImageInpaint-Setup-x64.exe`, `ImageInpaint-Setup-x64.exe.sha256`, setup installer smoke, installed launch smoke, and manual non-developer Windows user smoke within five minutes. The zip remains a portable fallback. | `packaging/build-windows.ps1 -RuntimeDir ... -Installer`, `packaging/verify-windows-installer-smoke.ps1 -RequireIopaint`, `packaging/verify-windows-zip-smoke.ps1 -FullExtract`, manual evidence. |
| macOS Apple Silicon users can open a dmg/app without Python or the command line. | Apple Silicon real-runtime dmg, checksum, dmg smoke, installed launch smoke, Gatekeeper result, and manual non-developer user smoke within five minutes. | `Desktop real runtime release` on `macos-15`, `packaging/verify-macos-dmg-smoke.sh --require-iopaint`, `packaging/verify-macos-install-smoke.sh --require-iopaint`, manual evidence. |
| macOS Intel users can open a dmg/app without Python or the command line. | Intel real-runtime dmg, checksum, dmg smoke, installed launch smoke, Gatekeeper result, and manual non-developer user smoke within five minutes. | `Desktop real runtime release` on `macos-15-intel`, `packaging/verify-macos-dmg-smoke.sh --require-iopaint`, `packaging/verify-macos-install-smoke.sh --require-iopaint`, manual evidence. |
| Public macOS artifacts pass Gatekeeper expectations. | Signed and notarized dmg, stapled ticket validation, `spctl` assessment, and final published artifact matching the notarized dmg. | `notarize_macos=true`, `packaging/sign-notarize-macos.sh`, `xcrun stapler validate`, `spctl --assess --type open`. |
| GUI supports the normal user workflow. | User can select Markdown, see local images, choose masks or fallback area, skip images, choose output, start processing, watch progress, cancel when possible, and open output/result/log. | GUI tests, packaged process smoke, manual user smoke. |
| Runtime checks and first-run model behavior are understandable. | Startup check shows runtime state, model cache path, free space, first-run model download note, and retry/log guidance. | `python -m md_image_inpaint.desktop_app --smoke-check`, GUI tests. |
| Original files are not modified. | Processing produces independent output directories with rewritten document, processed images, backups, and logs while original Markdown and images retain their hashes. | `--process-smoke`, `packaging/verify-release-windows.ps1`, `packaging/verify-release-macos.sh`, manual evidence. |
| Pre-check/dry-run explains what will happen before processing. | Dry-run identifies processable, skipped, missing, remote, unsupported, mask-mismatched, and selected-to-skip images without writing output. | Runner tests, GUI tests, manual user smoke. |
| Errors are human-readable while technical logs remain available. | Permission, missing file, low disk space, missing runtime/model, remote image, missing image, unsupported format, and mask mismatch have user-readable summaries and detailed logs. | Unit tests, troubleshooting docs, manual error-message spot checks. |
| Responsible use is visible. | README, package README, GUI notice, user guide, release notes, and evidence template warn against unauthorized removal of protected content. | Documentation tests and manual release evidence. |
| CLI remains available for developers and automation. | `image-inpaint`/`md-image-inpaint` console scripts and `python -m md_image_inpaint` still work. | CLI tests and README examples. |
| Dependency/runtime boundaries are clean. | No `.runtime`, `.model-cache`, `dist`, `release`, model weights, private documents, or processed user output are tracked. | `python packaging/verify-repository-boundaries.py`. |
| Release artifacts are complete and verifiable. | Zip/dmg files and matching canonical `.sha256` sidecars are uploaded; checksum verification passes before upload. | `python packaging/verify-checksum.py <artifact>`, workflow upload gates. |
| Documentation covers users and developers. | User, Windows, macOS, troubleshooting, development, release checklist, evidence template, and this matrix are present and linked. | Documentation tests and release review. |

## Completion Rule

Automated tests and local Windows evidence are not enough to mark the desktop
goal complete. Completion also requires current macOS Apple Silicon and Intel
real-runtime artifacts, notarization evidence for public macOS releases, and
manual non-developer user smoke results for Windows and macOS.
