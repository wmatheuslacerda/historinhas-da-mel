import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ESCALA, OFF_Y, SH, SOBREPOE, SW} from './dados';

export type Camera = {
  fx: number; // ponto de foco no palco
  fy: number;
  s0: number; // zoom inicial
  s1: number; // zoom final
  px?: number; // deslocamento (pan) ao longo da cena, em px do palco
  py?: number;
  tremer?: {quadro: number; amp: number}; // sacudida (ex.: chegada do Davi)
};

type Props = {
  n: number; // número da cena (fundo)
  duracao: number; // quadros da Sequence
  primeira?: boolean;
  camera: Camera;
  palco: React.ReactNode; // personagens (coordenadas do palco)
  tela?: React.ReactNode; // efeitos em coordenadas da tela
  tom?: string; // cor para "colorir" a cena
};

export const Cena: React.FC<Props> = ({n, duracao, primeira, camera, palco, tela, tom}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = interpolate(f, [0, duracao], [0, 1], {extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
  const s = camera.s0 + (camera.s1 - camera.s0) * p;
  let tx = (camera.px ?? 0) * p;
  let ty = (camera.py ?? 0) * p;
  if (camera.tremer) {
    const d = f - camera.tremer.quadro;
    if (d >= 0) {
      const a = camera.tremer.amp * Math.exp(-d / 6);
      tx += a * Math.sin(d * 2.1);
      ty += a * 0.6 * Math.cos(d * 2.7);
    }
  }
  const opacidade = primeira ? 1 : interpolate(f, [0, SOBREPOE], [0, 1], {extrapolateRight: 'clamp'});
  // leve "respiro" da câmera para nunca ficar parada
  const flutua = Math.sin(f / fps / 2.2) * 4;

  return (
    <AbsoluteFill style={{opacity: opacidade, overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: OFF_Y,
          width: SW,
          height: SH,
          transform: `scale(${ESCALA})`,
          transformOrigin: '0 0',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: SW,
            height: SH,
            transformOrigin: `${camera.fx}px ${camera.fy}px`,
            transform: `translate(${tx}px, ${ty + flutua}px) scale(${s})`,
          }}
        >
          <Img src={staticFile(`camadas/fundo${n}.jpg`)} style={{position: 'absolute', width: SW, height: SH}} />
          {palco}
        </div>
      </div>
      {tom ? <AbsoluteFill style={{background: tom, mixBlendMode: 'multiply'}} /> : null}
      {tela}
    </AbsoluteFill>
  );
};
