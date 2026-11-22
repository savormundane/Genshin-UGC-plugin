function OnStart()
    script.object.showCursor = true
    local button = script.object:FindChild("Action")
    button:AddCursorEventListener(Enum.CursorEventType.CursorClick, function()
        print("Button clicked")
    end)
end
