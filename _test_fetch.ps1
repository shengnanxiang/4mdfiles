$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$baseUrl = "http://127.0.0.1:3845/mcp"
$workDir = "c:\Users\Nan\Documents\GitHub\4mdfiles"

Add-Type -AssemblyName "System.Net.Http"
$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromSeconds(120)

# Step 1: Initialize
$initJson = '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codebuddy","version":"1.0"}},"id":1}'
$content = New-Object System.Net.Http.StringContent($initJson, [System.Text.Encoding]::UTF8, "application/json")
$req = New-Object System.Net.Http.HttpRequestMessage("POST", $baseUrl)
$req.Content = $content
$req.Headers.Add("Accept", "application/json, text/event-stream")
$resp = $client.SendAsync($req, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
$sessionId = $resp.Headers.GetValues("mcp-session-id")[0]
Write-Host "Session: $sessionId"
$initBody = $resp.Content.ReadAsStringAsync().Result
Write-Host "Init response length: $($initBody.Length)"

# Step 2: Send initialized notification
$notifJson = '{"jsonrpc":"2.0","method":"notifications/initialized"}'
$content2 = New-Object System.Net.Http.StringContent($notifJson, [System.Text.Encoding]::UTF8, "application/json")
$req2 = New-Object System.Net.Http.HttpRequestMessage("POST", $baseUrl)
$req2.Content = $content2
$req2.Headers.Add("Accept", "application/json, text/event-stream")
$req2.Headers.Add("mcp-session-id", $sessionId)
$resp2 = $client.SendAsync($req2).Result
Write-Host "Notif status: $($resp2.StatusCode)"

# Step 3: Fetch test node - read as stream
$callJson = '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_design_context","arguments":{"nodeId":"1:2066","clientLanguages":"unknown","clientFrameworks":"unknown","disableCodeConnect":true}},"id":2}'
$content3 = New-Object System.Net.Http.StringContent($callJson, [System.Text.Encoding]::UTF8, "application/json")
$req3 = New-Object System.Net.Http.HttpRequestMessage("POST", $baseUrl)
$req3.Content = $content3
$req3.Headers.Add("Accept", "application/json, text/event-stream")
$req3.Headers.Add("mcp-session-id", $sessionId)
$resp3 = $client.SendAsync($req3, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
Write-Host "Call status: $($resp3.StatusCode)"
Write-Host "Content-Type: $($resp3.Content.Headers.ContentType)"

$stream = $resp3.Content.ReadAsStreamAsync().Result
$reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
$fullText = ""
while (-not $reader.EndOfStream) {
    $line = $reader.ReadLine()
    $fullText += $line + "`n"
}
$reader.Close()
Write-Host "Call response length: $($fullText.Length)"
[System.IO.File]::WriteAllText("$workDir\_test_resp.txt", $fullText, $utf8NoBom)
if ($fullText.Length -gt 3000) {
    Write-Host $fullText.Substring(0,3000)
} else {
    Write-Host $fullText
}
