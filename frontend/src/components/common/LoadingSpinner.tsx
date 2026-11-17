import React from 'react';
import { Scale } from 'lucide-react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({
  message = 'Compiling statutory framework and judicial authorities...'
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 space-y-4">
      <div className="relative">
        <div className="w-12 h-12 border-[3px] border-gold-300 border-t-navy-900 rounded-full animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Scale className="w-5 h-5 text-burgundy-900" />
        </div>
      </div>
      <p className="text-sm font-medium text-charcoal-600 font-serif">{message}</p>
    </div>
  );
};
