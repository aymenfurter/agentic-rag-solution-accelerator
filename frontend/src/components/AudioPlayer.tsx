import React from 'react';
import { Stack, DefaultButton } from '@fluentui/react';

interface AudioPlayerProps {
  audioUrl: string;
  jumpTime?: number;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, jumpTime }) => {
  const audioRef = React.useRef<HTMLAudioElement>(null);

  const handleJump = () => {
    if (audioRef.current && jumpTime) {
      audioRef.current.currentTime = jumpTime;
      audioRef.current.play();
    }
  };

  return (
    <Stack horizontal tokens={{ childrenGap: 10 }}>
      <audio ref={audioRef} src={audioUrl} controls />
      {jumpTime && (
        <DefaultButton text="Jump to Highlight" onClick={handleJump} />
      )}
    </Stack>
  );
};

export default AudioPlayer;