import {Composition} from 'remotion';
import {Ep1} from './Ep1';
import {roteiro} from './dados';

export const RemotionRoot: React.FC = () => (
  <Composition id="Ep1" component={Ep1} durationInFrames={roteiro.duracao} fps={30} width={1080} height={1920} />
);
