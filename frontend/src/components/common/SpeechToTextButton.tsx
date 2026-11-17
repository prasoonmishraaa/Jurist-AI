import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, AlertCircle, CheckCircle2, Volume2 } from 'lucide-react';

interface SpeechToTextButtonProps {
  onTranscript: (transcript: string) => void;
  className?: string;
  size?: 'sm' | 'md';
  title?: string;
  appendMode?: boolean;
}

// Polyfill types for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

export const SpeechToTextButton: React.FC<SpeechToTextButtonProps> = ({
  onTranscript,
  className = '',
  size = 'md',
  title = 'Dictate legal query using microphone',
  appendMode = true
}) => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [feedbackType, setFeedbackType] = useState<'info' | 'error' | 'success'>('info');
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-IN'; // Default to Indian English legal accents, works universally

      recognition.onstart = () => {
        setIsListening(true);
        setFeedbackType('info');
        setFeedbackMessage('Listening... Speak your legal facts or query (will not auto-submit).');
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript.trim()) {
          onTranscript(finalTranscript.trim());
          setFeedbackType('success');
          setFeedbackMessage('Transcript inserted into input. Review and confirm before submitting.');
          setTimeout(() => setFeedbackMessage(null), 4000);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        setIsListening(false);
        setFeedbackType('error');
        if (event.error === 'not-allowed' || event.error === 'permission-denied') {
          setFeedbackMessage(
            'Microphone access denied. Please grant microphone permission in your browser address bar to dictate.'
          );
        } else if (event.error === 'no-speech') {
          setFeedbackMessage('No speech detected. Please try speaking closer to the microphone.');
          setTimeout(() => setFeedbackMessage(null), 3500);
        } else {
          setFeedbackMessage(`Dictation error: ${event.error || 'Microphone unreachable'}`);
          setTimeout(() => setFeedbackMessage(null), 4000);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch {
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, [onTranscript]);

  const toggleListening = () => {
    if (!isSupported) {
      setFeedbackType('error');
      setFeedbackMessage(
        'Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.'
      );
      setTimeout(() => setFeedbackMessage(null), 5000);
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch {
        // ignore
      }
      setIsListening(false);
      setFeedbackMessage(null);
    } else {
      try {
        setFeedbackMessage(null);
        recognitionRef.current?.start();
      } catch (err: any) {
        setFeedbackType('error');
        setFeedbackMessage('Unable to start speech recognition. Please check microphone settings.');
      }
    }
  };

  const buttonSizeClasses =
    size === 'sm'
      ? 'p-1.5 text-xs'
      : 'p-2 text-sm';

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleListening}
        title={isListening ? 'Stop listening' : title}
        aria-label={isListening ? 'Stop speech recognition' : title}
        className={`inline-flex items-center justify-center rounded border transition-all ${
          isListening
            ? 'bg-red-600 text-white border-red-700 animate-pulse ring-2 ring-red-400 shadow-sm'
            : isSupported
            ? 'bg-ivory-50 text-navy-900 border-ivory-300 hover:border-gold-500 hover:bg-gold-50'
            : 'bg-ivory-100 text-charcoal-400 border-ivory-300 cursor-not-allowed opacity-60'
        } ${buttonSizeClasses} ${className}`}
      >
        {isListening ? (
          <MicOff className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
        ) : (
          <Mic className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
        )}
      </button>

      {/* Floating feedback alert */}
      {feedbackMessage && (
        <div
          role="status"
          className={`absolute left-0 top-full mt-1.5 z-30 w-72 p-2.5 rounded shadow-lg text-[11px] leading-tight flex items-start gap-2 border font-sans ${
            feedbackType === 'error'
              ? 'bg-burgundy-50 border-burgundy-300 text-burgundy-950'
              : feedbackType === 'success'
              ? 'bg-green-50 border-green-300 text-green-950'
              : 'bg-navy-900 border-gold-500/50 text-gold-200'
          }`}
        >
          {feedbackType === 'error' && (
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-burgundy-700" />
          )}
          {feedbackType === 'success' && (
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-green-700" />
          )}
          {feedbackType === 'info' && (
            <Volume2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-gold-400 animate-pulse" />
          )}
          <span className="flex-1">{feedbackMessage}</span>
          <button
            type="button"
            onClick={() => setFeedbackMessage(null)}
            className="text-[10px] opacity-70 hover:opacity-100 underline shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};
