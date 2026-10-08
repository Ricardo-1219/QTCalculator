param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$WaitMs = 2000,
    [string]$Keys = ""
)

Add-Type -AssemblyName System.Drawing

$sig = @'
using System;
using System.Runtime.InteropServices;
public class Win32Grab {
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
if (-not ("Win32Grab" -as [type])) { Add-Type -TypeDefinition $sig }

$proc = Start-Process -FilePath $Exe -PassThru
Start-Sleep -Milliseconds $WaitMs
$proc.Refresh()
$h = $proc.MainWindowHandle
for ($i = 0; $i -lt 20 -and $h -eq [IntPtr]::Zero; $i++)
{
    Start-Sleep -Milliseconds 300
    $proc.Refresh()
    $h = $proc.MainWindowHandle
}
if ($h -eq [IntPtr]::Zero)
{
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw "no main window"
}

[void][Win32Grab]::MoveWindow($h, 60, 60, 560, 650, $true)
Start-Sleep -Milliseconds 800

#  直接向窗口投递按键消息，不依赖窗口是否处于前台，结果可复现。
#  普通字符用 WM_CHAR；功能键用 WM_KEYDOWN / WM_KEYUP。
#  记号：~ 回车，< 退格，! ESC
if ($Keys -ne "")
{
    foreach ($ch in $Keys.ToCharArray())
    {
        $isSpecial = $false
        $vk = 0

        if ($ch -eq '~')
        {
            $isSpecial = $true
            $vk = 0x0D
        }
        elseif ($ch -eq '<')
        {
            $isSpecial = $true
            $vk = 0x08
        }
        elseif ($ch -eq '!')
        {
            $isSpecial = $true
            $vk = 0x1B
        }

        if ($isSpecial)
        {
            [void][Win32Grab]::PostMessage($h, 0x0100, [IntPtr]$vk, [IntPtr]0)
            Start-Sleep -Milliseconds 40
            [void][Win32Grab]::PostMessage($h, 0x0101, [IntPtr]$vk, [IntPtr]0)
        }
        else
        {
            [void][Win32Grab]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0)
        }
        Start-Sleep -Milliseconds 90
    }
    Start-Sleep -Milliseconds 700
}

$r = New-Object Win32Grab+RECT
[void][Win32Grab]::GetWindowRect($h, [ref]$r)
$w = $r.Right - $r.Left
$hh = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap($w, $hh)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][Win32Grab]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Write-Output "saved $Out ($w x $hh)"
