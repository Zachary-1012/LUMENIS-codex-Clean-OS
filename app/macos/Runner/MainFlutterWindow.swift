import Cocoa
import FlutterMacOS
import macos_window_utils
import AVFoundation

class MainFlutterWindow: NSWindow {
  override func awakeFromNib() {
    let windowFrame = self.frame
    let macOSWindowUtilsViewController = MacOSWindowUtilsViewController()
    self.contentViewController = macOSWindowUtilsViewController
    self.setFrame(windowFrame, display: true)

    MainFlutterWindowManipulator.start(mainFlutterWindow: self)
    RegisterGeneratedPlugins(registry: macOSWindowUtilsViewController.flutterViewController)
    LocalReadAloudBridge.shared.install(
      messenger: macOSWindowUtilsViewController.flutterViewController.engine.binaryMessenger
    )

    super.awakeFromNib()
  }
}

private final class LocalReadAloudBridge: NSObject, AVSpeechSynthesizerDelegate {
  static let shared = LocalReadAloudBridge()
  private let synthesizer = AVSpeechSynthesizer()
  private var status = "STOPPED"
  private var currentUtterance: AVSpeechUtterance?

  private override init() {
    super.init()
    synthesizer.delegate = self
  }

  func install(messenger: FlutterBinaryMessenger) {
    let channel = FlutterMethodChannel(name: "lumenis/read_aloud", binaryMessenger: messenger)
    channel.setMethodCallHandler { [weak self] call, result in
      guard let self else { result(FlutterError(code: "UNAVAILABLE", message: "Speech bridge unavailable.", details: nil)); return }
      switch call.method {
      case "availableLocales":
        result(["supported": true, "localLocales": self.localLocales()])
      case "speak":
        self.speak(call.arguments as? [String: Any], result: result)
      case "stop":
        self.currentUtterance = nil
        self.synthesizer.stopSpeaking(at: .immediate)
        self.status = "STOPPED"
        result(nil)
      case "observe":
        result(["status": self.status])
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private func localLocales() -> [String] {
    let tags = Set(localVoices().compactMap { canonicalTag($0.language) })
    return ["zh-CN", "en-US", "ko-KR"].filter { tags.contains($0) }
  }

  private func localVoices() -> [AVSpeechSynthesisVoice] {
    AVSpeechSynthesisVoice.speechVoices().filter { $0.identifier.hasPrefix("com.apple.") }
  }

  private func canonicalTag(_ raw: String) -> String? {
    switch raw.replacingOccurrences(of: "_", with: "-").lowercased() {
    case "zh-cn": return "zh-CN"
    case "en-us": return "en-US"
    case "ko-kr": return "ko-KR"
    default: return nil
    }
  }

  private func speak(_ arguments: [String: Any]?, result: @escaping FlutterResult) {
    guard let text = arguments?["text"] as? String, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
          let locale = arguments?["locale"] as? String, let rate = arguments?["rate"] as? NSNumber,
          [0.75, 1.0, 1.25].contains(rate.doubleValue),
          let voice = localVoices().first(where: { canonicalTag($0.language) == locale }) else {
      result(["status": "UNAVAILABLE"])
      return
    }
    currentUtterance = nil
    synthesizer.stopSpeaking(at: .immediate)
    let utterance = AVSpeechUtterance(string: text)
    utterance.voice = voice
    utterance.rate = Float(min(max(Double(AVSpeechUtteranceDefaultSpeechRate) * rate.doubleValue, Double(AVSpeechUtteranceMinimumSpeechRate)), Double(AVSpeechUtteranceMaximumSpeechRate)))
    status = "STARTING"
    currentUtterance = utterance
    synthesizer.speak(utterance)
    result(["status": "STARTING"])
  }

  func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didStart utterance: AVSpeechUtterance) {
    guard currentUtterance === utterance else { return }
    status = "PLAYING"
  }

  func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
    guard currentUtterance === utterance else { return }
    currentUtterance = nil
    status = "COMPLETED"
  }

  func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
    guard currentUtterance === utterance else { return }
    currentUtterance = nil
    status = "STOPPED"
  }
}
