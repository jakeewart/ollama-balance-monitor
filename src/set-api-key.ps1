param (
    [switch]$Silent
)

Add-Type -AssemblyName System.Windows.Forms

# Skip UI in silent mode if a key is already set.
$existingKey = [Environment]::GetEnvironmentVariable("OLLAMA_API_KEY", "User")
if ($Silent -and -not [string]::IsNullOrWhiteSpace($existingKey)) {
    Write-Host "Existing OLLAMA_API_KEY preserved."
    exit 0
}

# Script is in src/; assets is in the parent directory.
$repoRoot = Split-Path -Parent $PSScriptRoot
$iconPath = Join-Path $repoRoot "assets\ollama.ico"
if (-not (Test-Path $iconPath)) {
    $iconPath = $null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Ollama Balance Monitor"
$form.Width = 520
$form.Height = 220
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false

if ($iconPath) {
    $form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath)
}

$label = New-Object System.Windows.Forms.Label
$label.Text = "Enter Ollama Cloud API Key:"
$label.Left = 20
$label.Top = 20
$label.Width = 460
$label.Height = 20
$form.Controls.Add($label)

$textBox = New-Object System.Windows.Forms.TextBox
$textBox.Left = 20
$textBox.Top = 50
$textBox.Width = 460
$textBox.Height = 25
$textBox.UseSystemPasswordChar = $true
$form.Controls.Add($textBox)

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = "OK"
$okButton.Left = 300
$okButton.Top = 100
$okButton.Width = 80
$okButton.Height = 30
$okButton.Add_Click({
    $apiKey = $textBox.Text.Trim()
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        [System.Windows.Forms.MessageBox]::Show("Please enter an API key.", "API Key Required", "OK", "Warning")
        return
    }
    $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Close()
})
$form.Controls.Add($okButton)

$skipButton = New-Object System.Windows.Forms.Button
$skipButton.Text = "Skip"
$skipButton.Left = 400
$skipButton.Top = 100
$skipButton.Width = 80
$skipButton.Height = 30
$skipButton.Add_Click({
    $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Close()
})
$form.Controls.Add($skipButton)

$result = $form.ShowDialog()

if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    if (-not $Silent) {
        Write-Host "API key entry skipped. No changes made."
    }
    exit 0
}

$apiKey = $textBox.Text.Trim()

[Environment]::SetEnvironmentVariable("OLLAMA_API_KEY", $apiKey, "User")
$env:OLLAMA_API_KEY = $apiKey

if (-not $Silent) {
    [System.Windows.Forms.MessageBox]::Show("API key saved for this user. It will be available after restarting any open applications.", "Saved", "OK", "Information")
}

Write-Host "OLLAMA_API_KEY set successfully."