import {AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig} from 'remotion';

/** Poeirinha de luz flutuando */
export const Poeira: React.FC<{cor: string; n: number; seed: string; brilho?: number}> = ({cor, n, seed, brilho = 1}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {Array.from({length: n}).map((_, i) => {
        const x0 = random(`${seed}x${i}`) * 1080;
        const y0 = random(`${seed}y${i}`) * 1920;
        const vel = 18 + random(`${seed}v${i}`) * 45;
        const tam = 3 + random(`${seed}s${i}`) * 8;
        const ph = random(`${seed}p${i}`) * 6.28;
        const y = (((y0 - vel * t) % 1920) + 1920) % 1920;
        const x = x0 + 22 * Math.sin(t * 0.7 + ph);
        const op = brilho * (0.2 + 0.5 * (0.5 + 0.5 * Math.sin(t * 2.2 + ph)));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: tam,
              height: tam,
              borderRadius: '50%',
              background: cor,
              opacity: op,
              boxShadow: `0 0 ${tam * 2.5}px ${cor}`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const CORACAO = 'M12 21s-7.5-4.6-10-9.3C.4 8.6 2.1 5 5.6 5c2 0 3.4 1.1 4.4 2.5C11 6.1 12.4 5 14.4 5 17.9 5 19.6 8.6 18 11.7 15.5 16.4 12 21 12 21z';

/** Corações subindo (risada) */
export const Coracoes: React.FC<{ini: number; fim: number; seed: string; n?: number}> = ({ini, fim, seed, n = 12}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {Array.from({length: n}).map((_, i) => {
        const nasce = ini + random(`${seed}n${i}`) * Math.max(1, fim - ini);
        const vida = 55 + random(`${seed}l${i}`) * 30;
        const d = f - nasce;
        if (d < 0 || d > vida) return null;
        const p = d / vida;
        const lado = i % 2 === 0 ? 90 + random(`${seed}x${i}`) * 230 : 760 + random(`${seed}x${i}`) * 230;
        const x = lado + 40 * Math.sin(d * 0.12 + i);
        const y = 1250 - p * 700;
        const s = (0.6 + random(`${seed}s${i}`) * 0.9) * interpolate(p, [0, 0.15, 1], [0.2, 1, 0.9]);
        const op = interpolate(p, [0, 0.1, 0.75, 1], [0, 1, 0.9, 0]);
        const cor = i % 3 === 0 ? '#FFD54F' : i % 3 === 1 ? '#FF6B8A' : '#FF8FB1';
        return (
          <svg
            key={i}
            viewBox="0 0 20 22"
            width={70}
            height={70}
            style={{position: 'absolute', left: x, top: y, opacity: op, transform: `scale(${s}) rotate(${Math.sin(d * 0.1 + i) * 15}deg)`}}
          >
            <path d={CORACAO} fill={cor} stroke="rgba(255,255,255,0.85)" strokeWidth={1.2} />
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};

/** Estrelinhas piscando */
export const Estrelas: React.FC<{seed: string; n?: number}> = ({seed, n = 10}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {Array.from({length: n}).map((_, i) => {
        const x = 120 + random(`${seed}x${i}`) * 840;
        const y = 300 + random(`${seed}y${i}`) * 900;
        const per = 40 + random(`${seed}p${i}`) * 40;
        const ph = random(`${seed}f${i}`) * per;
        const v = Math.max(0, Math.sin(((f + ph) / per) * Math.PI * 2));
        const s = 0.4 + v * 0.8;
        return (
          <svg key={i} viewBox="-10 -10 20 20" width={46} height={46} style={{position: 'absolute', left: x, top: y, opacity: v, transform: `scale(${s}) rotate(${f * 2}deg)`}}>
            <path d="M0 -9 L2 -2 L9 0 L2 2 L0 9 L-2 2 L-9 0 L-2 -2 Z" fill="#FFF4C2" />
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};

/** Raios de luz do pôr do sol */
export const Raios: React.FC<{cor?: string}> = ({cor = '255,205,130'}) => {
  const f = useCurrentFrame();
  const op = 0.65 + 0.35 * Math.sin(f / 40);
  const dx = Math.sin(f / 90) * 60;
  return (
    <AbsoluteFill
      style={{
        mixBlendMode: 'screen',
        opacity: op,
        transform: `translateX(${dx}px)`,
        background: `linear-gradient(115deg, rgba(${cor},0) 18%, rgba(${cor},0.20) 30%, rgba(${cor},0) 40%, rgba(${cor},0.14) 52%, rgba(${cor},0) 62%)`,
      }}
    />
  );
};

export const Vinheta: React.FC<{forca?: number}> = ({forca = 0.5}) => (
  <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(10,5,20,${forca}) 100%)`}} />
);
