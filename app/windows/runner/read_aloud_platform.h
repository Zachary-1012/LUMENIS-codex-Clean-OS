#ifndef RUNNER_READ_ALOUD_PLATFORM_H_
#define RUNNER_READ_ALOUD_PLATFORM_H_

#include <flutter/method_channel.h>
#include <flutter/standard_method_codec.h>

#include <memory>
#include <string>

#include <sapi.h>

class ReadAloudPlatform {
 public:
  explicit ReadAloudPlatform(flutter::BinaryMessenger* messenger);
  ~ReadAloudPlatform();

  ReadAloudPlatform(const ReadAloudPlatform&) = delete;
  ReadAloudPlatform& operator=(const ReadAloudPlatform&) = delete;

  void Stop();

 private:
  void HandleMethodCall(
      const flutter::MethodCall<flutter::EncodableValue>& call,
      std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>> result);
  flutter::EncodableList LocalLocales();
  ISpObjectToken* FindLocalVoice(const std::string& locale);
  std::string Observe();

  std::unique_ptr<flutter::MethodChannel<flutter::EncodableValue>> channel_;
  ISpVoice* voice_ = nullptr;
  std::string status_ = "STOPPED";
  bool com_initialized_ = false;
};

#endif  // RUNNER_READ_ALOUD_PLATFORM_H_
