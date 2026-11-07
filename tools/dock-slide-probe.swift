// Times the macOS Dock's auto-hide slide: moves the pointer to the bottom edge and back
// (no clicks), logging every change in the Dock's window bounds and AX position.
import Cocoa

func now() -> Double { Date().timeIntervalSince1970 }
let t0 = now()
func log(_ s: String) { print(String(format: "%7.1f ms  %@", (now() - t0) * 1000, s)) }

print("AX trusted:", AXIsProcessTrusted())
for s in NSScreen.screens { print("screen", s.frame) }
let main = CGDisplayBounds(CGMainDisplayID())
print("main", main)

guard let dock = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.dock").first else { fatalError("no dock") }
let ax = AXUIElementCreateApplication(dock.processIdentifier)
var list: AXUIElement?
var kids: CFTypeRef?
if AXUIElementCopyAttributeValue(ax, kAXChildrenAttribute as CFString, &kids) == .success, let arr = kids as? [AXUIElement] {
    for k in arr {
        var role: CFTypeRef?
        AXUIElementCopyAttributeValue(k, kAXRoleAttribute as CFString, &role)
        if (role as? String) == "AXList" { list = k; break }
    }
}
print("AX list found:", list != nil)

func axPosition() -> String {
    guard let l = list else { return "-" }
    var v: CFTypeRef?
    guard AXUIElementCopyAttributeValue(l, kAXPositionAttribute as CFString, &v) == .success, let val = v else { return "-" }
    var p = CGPoint.zero
    AXValueGetValue(val as! AXValue, .cgPoint, &p)
    return "\(Int(p.x)),\(Int(p.y))"
}

func windows() -> String {
    guard let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] else { return "" }
    var out: [String] = []
    for w in info where (w[kCGWindowOwnerName as String] as? String) == "Dock" {
        let b = w[kCGWindowBounds as String] as? [String: Any] ?? [:]
        let layer = w[kCGWindowLayer as String] as? Int ?? -1
        let alpha = w[kCGWindowAlpha as String] as? Double ?? -1
        out.append("L\(layer) y=\(b["Y"] ?? "?") h=\(b["Height"] ?? "?") w=\(b["Width"] ?? "?") a=\(alpha)")
    }
    return out.sorted().joined(separator: " | ")
}

func move(_ p: CGPoint) {
    CGWarpMouseCursorPosition(p)
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
}

let original = CGEvent(source: nil)?.location ?? .zero
let cx = main.midX
let above = CGPoint(x: cx, y: main.maxY - 300)
let edge = CGPoint(x: cx, y: main.maxY - 1)

var lastW = windows(), lastA = axPosition()
print("initial windows:", lastW)
print("initial ax:", lastA)

func poll(_ seconds: Double) {
    let end = now() + seconds
    while now() < end {
        let a = axPosition()
        if a != lastA { log("ax \(a)"); lastA = a }
        let w = windows()
        if w != lastW { log("win \(w)"); lastW = w }
    }
}

move(above)
poll(0.2)
log("MOVE TO EDGE")
// Dock reveals on motion into the bottom edge, so approach it over a few events.
for i in stride(from: 40, through: 1, by: -3) { move(CGPoint(x: cx, y: main.maxY - CGFloat(i))); usleep(4000) }
move(edge)
poll(1.3)
log("MOVE AWAY")
move(above)
poll(1.3)
move(original)
print("restored pointer to", original)
