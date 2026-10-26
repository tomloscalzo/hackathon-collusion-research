param($dir)
$c = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$sizes = Get-Content "$dir\_sizes.json" | ConvertFrom-Json
foreach ($s in $sizes) {
  & $c --headless=new --disable-gpu --hide-scrollbars "--screenshot=$dir\$($s.file).png" "--window-size=$($s.W),$($s.H)" "file:///$dir/$($s.file).html" 2>$null | Out-Null
}
