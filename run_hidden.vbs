Option Explicit

Dim shell, scriptPath, command
Set shell = CreateObject("WScript.Shell")

If WScript.Arguments.Count <> 1 Then
    WScript.Quit 2
End If

scriptPath = WScript.Arguments(0)
command = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File " & Quote(scriptPath)
shell.Run command, 0, True

Function Quote(value)
    Quote = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
