#include "read_aloud_platform.h"

#include <algorithm>
#include <cwchar>
#include <cwctype>
#include <string>
#include <vector>

#include <flutter/encodable_value.h>
#include <objbase.h>

namespace {

using flutter::EncodableList;
using flutter::EncodableMap;
using flutter::EncodableValue;

const EncodableValue* FindValue(const EncodableMap* map, const char* key) {
  if (!map) return nullptr;
  const auto found = map->find(EncodableValue(key));
  return found == map->end() ? nullptr : &found->second;
}

std::string CanonicalTag(std::wstring language_ids) {
  std::wstring id;
  for (wchar_t c : language_ids) {
    if (std::iswxdigit(c)) {
      id.push_back(static_cast<wchar_t>(std::towlower(c)));
    } else if (!id.empty()) {
      const auto value = std::wcstoul(id.c_str(), nullptr, 16);
      if (value == 0x0804) return "zh-CN";
      if (value == 0x0409) return "en-US";
      if (value == 0x0412) return "ko-KR";
      id.clear();
    }
  }
  if (!id.empty()) {
    const auto value = std::wcstoul(id.c_str(), nullptr, 16);
    if (value == 0x0804) return "zh-CN";
    if (value == 0x0409) return "en-US";
    if (value == 0x0412) return "ko-KR";
  }
  std::transform(language_ids.begin(), language_ids.end(), language_ids.begin(),
                 [](wchar_t c) { return static_cast<wchar_t>(std::towlower(c)); });
  if (language_ids.find(L"0804") != std::wstring::npos ||
      language_ids.find(L"zh-cn") != std::wstring::npos) {
    return "zh-CN";
  }
  if (language_ids.find(L"0409") != std::wstring::npos ||
      language_ids.find(L"en-us") != std::wstring::npos) {
    return "en-US";
  }
  if (language_ids.find(L"0412") != std::wstring::npos ||
      language_ids.find(L"ko-kr") != std::wstring::npos) {
    return "ko-KR";
  }
  return {};
}

std::wstring ToWide(const std::string& text) {
  if (text.empty()) return {};
  const int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS,
                                       text.data(), static_cast<int>(text.size()),
                                       nullptr, 0);
  if (size <= 0) return {};
  std::wstring result(size, L'\0');
  MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(),
                      static_cast<int>(text.size()), result.data(), size);
  return result;
}

EncodableValue StatusResult(const std::string& status) {
  return EncodableValue(EncodableMap{
      {EncodableValue("status"), EncodableValue(status)},
  });
}

}  // namespace

ReadAloudPlatform::ReadAloudPlatform(flutter::BinaryMessenger* messenger)
    : channel_(std::make_unique<flutter::MethodChannel<EncodableValue>>(
          messenger, "lumenis/read_aloud",
          &flutter::StandardMethodCodec::GetInstance())) {
  const HRESULT com_result = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  com_initialized_ = SUCCEEDED(com_result);
  channel_->SetMethodCallHandler(
      [this](const flutter::MethodCall<EncodableValue>& call,
             std::unique_ptr<flutter::MethodResult<EncodableValue>> result) {
        HandleMethodCall(call, std::move(result));
      });
}

ReadAloudPlatform::~ReadAloudPlatform() {
  Stop();
  channel_->SetMethodCallHandler(nullptr);
  if (voice_) {
    voice_->Release();
    voice_ = nullptr;
  }
  if (com_initialized_) CoUninitialize();
}

void ReadAloudPlatform::Stop() {
  if (voice_) voice_->Speak(nullptr, SPF_PURGEBEFORESPEAK, nullptr);
  status_ = "STOPPED";
}

void ReadAloudPlatform::HandleMethodCall(
    const flutter::MethodCall<EncodableValue>& call,
    std::unique_ptr<flutter::MethodResult<EncodableValue>> result) {
  if (call.method_name() == "availableLocales") {
    EncodableMap response{
        {EncodableValue("supported"), EncodableValue(true)},
        {EncodableValue("localLocales"), EncodableValue(LocalLocales())},
    };
    result->Success(EncodableValue(response));
    return;
  }
  if (call.method_name() == "stop") {
    Stop();
    result->Success();
    return;
  }
  if (call.method_name() == "observe") {
    result->Success(StatusResult(Observe()));
    return;
  }
  if (call.method_name() != "speak") {
    result->NotImplemented();
    return;
  }

  const auto* args = std::get_if<EncodableMap>(call.arguments());
  const auto* text_value = FindValue(args, "text");
  const auto* locale_value = FindValue(args, "locale");
  const auto* rate_value = FindValue(args, "rate");
  const auto* text = text_value ? std::get_if<std::string>(text_value) : nullptr;
  const auto* locale = locale_value ? std::get_if<std::string>(locale_value) : nullptr;
  double rate = 1.0;
  bool valid_rate = false;
  if (rate_value) {
    if (const auto* double_value = std::get_if<double>(rate_value)) {
      rate = *double_value;
      valid_rate = true;
    } else if (const auto* integer_value = std::get_if<int32_t>(rate_value)) {
      rate = *integer_value;
      valid_rate = true;
    }
  }
  if (!text || text->empty() || !locale || !valid_rate ||
      (rate != .75 && rate != 1.0 && rate != 1.25)) {
    result->Success(StatusResult("FAILED"));
    return;
  }

  ISpObjectToken* token = FindLocalVoice(*locale);
  if (!token) {
    result->Success(StatusResult("UNAVAILABLE"));
    return;
  }
  if (!voice_ && FAILED(CoCreateInstance(CLSID_SpVoice, nullptr,
                                          CLSCTX_INPROC_SERVER, IID_ISpVoice,
                                          reinterpret_cast<void**>(&voice_)))) {
    token->Release();
    status_ = "FAILED";
    result->Success(StatusResult(status_));
    return;
  }
  HRESULT selected = voice_->SetVoice(token);
  token->Release();
  if (FAILED(selected)) {
    status_ = "FAILED";
    result->Success(StatusResult(status_));
    return;
  }
  const long sapi_rate = rate == .75 ? -2 : rate == 1.25 ? 2 : 0;
  voice_->SetRate(sapi_rate);
  const std::wstring spoken_text = ToWide(*text);
  if (spoken_text.empty()) {
    status_ = "FAILED";
    result->Success(StatusResult(status_));
    return;
  }
  status_ = "STARTING";
  const HRESULT spoken = voice_->Speak(spoken_text.c_str(),
                                        SPF_ASYNC | SPF_PURGEBEFORESPEAK,
                                        nullptr);
  if (FAILED(spoken)) {
    status_ = "FAILED";
    result->Success(StatusResult(status_));
    return;
  }
  result->Success(StatusResult(status_));
}

EncodableList ReadAloudPlatform::LocalLocales() {
  EncodableList found;
  for (const char* locale : {"zh-CN", "en-US", "ko-KR"}) {
    ISpObjectToken* token = FindLocalVoice(locale);
    if (token) {
      found.emplace_back(locale);
      token->Release();
    }
  }
  return found;
}

ISpObjectToken* ReadAloudPlatform::FindLocalVoice(const std::string& locale) {
  ISpObjectTokenCategory* category = nullptr;
  if (FAILED(CoCreateInstance(CLSID_SpObjectTokenCategory, nullptr,
                              CLSCTX_INPROC_SERVER,
                              IID_ISpObjectTokenCategory,
                              reinterpret_cast<void**>(&category))) ||
      !category) {
    return nullptr;
  }
  if (FAILED(category->SetId(SPCAT_VOICES, FALSE))) {
    category->Release();
    return nullptr;
  }
  IEnumSpObjectTokens* tokens = nullptr;
  const HRESULT enumeration = category->EnumTokens(nullptr, nullptr, &tokens);
  category->Release();
  if (FAILED(enumeration) || !tokens) {
    return nullptr;
  }
  ULONG count = 0;
  tokens->GetCount(&count);
  ISpObjectToken* match = nullptr;
  for (ULONG index = 0; index < count; ++index) {
    ISpObjectToken* token = nullptr;
    if (FAILED(tokens->Item(index, &token)) || !token) continue;
    ISpDataKey* attributes = nullptr;
    WCHAR* language = nullptr;
    const bool matching =
        SUCCEEDED(token->OpenKey(L"Attributes", &attributes)) && attributes &&
        SUCCEEDED(attributes->GetStringValue(L"Language", &language)) &&
        language && CanonicalTag(language) == locale;
    if (language) CoTaskMemFree(language);
    if (attributes) attributes->Release();
    if (matching) {
      match = token;
      break;
    }
    token->Release();
  }
  tokens->Release();
  return match;
}

std::string ReadAloudPlatform::Observe() {
  if (!voice_ || (status_ != "STARTING" && status_ != "PLAYING")) {
    return status_;
  }
  SPVOICESTATUS voice_status{};
  if (FAILED(voice_->GetStatus(&voice_status, nullptr))) {
    status_ = "FAILED";
  } else if (voice_status.dwRunningState == SPRS_IS_SPEAKING) {
    status_ = "PLAYING";
  } else if (voice_status.dwRunningState == SPRS_DONE) {
    status_ = "COMPLETED";
  }
  return status_;
}
