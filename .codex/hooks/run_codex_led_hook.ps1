$hookPath = Join-Path -Path $PSScriptRoot -ChildPath 'codex_led_hook.py'
$input | & python.exe $hookPath
exit $LASTEXITCODE
