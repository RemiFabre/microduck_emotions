// Render a line with AVSpeechSynthesizer exactly as Chrome does on macOS (pitchMultiplier = web pitch,
// rate mapped like Chromium's tts_mac.mm), to a wav. usage: avsay out.wav "text" [voiceName] [pitch] [webRate]
#import <AVFoundation/AVFoundation.h>
#import <Foundation/Foundation.h>
int main(int argc, char **argv) {
  @autoreleasepool {
    if (argc < 3) { fprintf(stderr, "usage: avsay out.wav text [voiceName=Daniel] [pitch=1.28] [webRate=1.02]\n"); return 1; }
    NSURL *out = [NSURL fileURLWithPath:@(argv[1])];
    NSString *text = @(argv[2]);
    NSString *voiceName = argc > 3 ? @(argv[3]) : @"Daniel";
    float pitch = argc > 4 ? atof(argv[4]) : 1.28f;
    float webRate = argc > 5 ? atof(argv[5]) : 1.02f;
    AVSpeechSynthesisVoice *voice = nil;
    for (AVSpeechSynthesisVoice *v in [AVSpeechSynthesisVoice speechVoices])
      if ([v.name hasPrefix:voiceName] && [v.language hasPrefix:@"en-GB"]) { voice = v; break; }
    if (!voice) for (AVSpeechSynthesisVoice *v in [AVSpeechSynthesisVoice speechVoices]) if ([v.name hasPrefix:voiceName]) { voice = v; break; }
    if (!voice) { fprintf(stderr, "no voice %s\n", argv[3]); return 2; }
    AVSpeechUtterance *u = [AVSpeechUtterance speechUtteranceWithString:text];
    u.voice = voice; u.pitchMultiplier = pitch;
    float def = AVSpeechUtteranceDefaultSpeechRate, mx = AVSpeechUtteranceMaximumSpeechRate;
    u.rate = webRate < 1 ? webRate * def : def + fminf((webRate - 1) / 3, 1) * (mx - def);
    fprintf(stderr, "voice %s (%s) rate %.3f pitch %.2f\n", voice.identifier.UTF8String, voice.language.UTF8String, u.rate, pitch);
    AVSpeechSynthesizer *synth = [[AVSpeechSynthesizer alloc] init];
    __block AVAudioFile *file = nil; __block BOOL done = NO; __block long frames = 0;
    [synth writeUtterance:u toBufferCallback:^(AVAudioBuffer *buf) {
      AVAudioPCMBuffer *pcm = (AVAudioPCMBuffer *)buf;
      if (![pcm isKindOfClass:[AVAudioPCMBuffer class]] || pcm.frameLength == 0) { done = YES; return; }
      NSError *err = nil;
      if (!file) file = [[AVAudioFile alloc] initForWriting:out settings:pcm.format.settings commonFormat:pcm.format.commonFormat interleaved:pcm.format.isInterleaved error:&err];
      if (err) { fprintf(stderr, "file: %s\n", err.localizedDescription.UTF8String); done = YES; return; }
      [file writeFromBuffer:pcm error:&err]; frames += pcm.frameLength;
    }];
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:60];
    while (!done && [deadline timeIntervalSinceNow] > 0) [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
    file = nil;
    printf("wrote %s (%ld frames)\n", argv[1], frames);
    return done ? 0 : 3;
  }
}
