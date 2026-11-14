// One Remotion project for every video. Each video keeps its own files under
// videos/<name>/ and is rendered with `--public-dir videos/<name>/`.
import type { CalculateMetadataFunction } from "remotion";
import { Composition, Still } from "remotion";
import { loadNarration } from "./brand/narration";
import { Sting } from "./Sting";
import { Thumbnail } from "./Thumbnail";
import { Video, type ExplainerProps } from "./WhatCameOfItExplainerVideo";

// Length comes from the narration, which is read from the video's folder at render time.
const withNarration: CalculateMetadataFunction<ExplainerProps> = async ({ props }) => {
  const { timing, captions } = await loadNarration();
  return { durationInFrames: timing.total_frames, fps: timing.fps, props: { ...props, timing, captions } };
};

const defaults: ExplainerProps = {
  orientation: "horizontal",
  showCaptions: true,
  timing: null,
  captions: null,
};

export const RemotionRoot = () => (
  <>
    <Composition
      id="WhatCameOfItExplainer"
      component={Video}
      width={3840}
      height={2160}
      fps={30}
      durationInFrames={300}
      defaultProps={defaults}
      calculateMetadata={withNarration}
    />
    <Composition
      id="WhatCameOfItExplainerVertical"
      component={Video}
      width={2160}
      height={3840}
      fps={30}
      durationInFrames={300}
      defaultProps={{ ...defaults, orientation: "vertical" }}
      calculateMetadata={withNarration}
    />
    <Still id="Thumbnail16x9" component={Thumbnail} width={1920} height={1080} />
    <Still id="Thumbnail4x3" component={Thumbnail} width={1200} height={900} />
    <Still id="Thumbnail9x16" component={Thumbnail} width={1080} height={1920} />
    {/* The logo sting: four silent seconds, for the end of a video and for posts. */}
    <Composition
      id="Sting"
      component={Sting}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={120}
      defaultProps={{ orientation: "horizontal" as const }}
    />
    <Composition
      id="StingSquare"
      component={Sting}
      width={1080}
      height={1080}
      fps={30}
      durationInFrames={120}
      defaultProps={{ orientation: "square" as const }}
    />
    <Composition
      id="StingVertical"
      component={Sting}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={120}
      defaultProps={{ orientation: "vertical" as const }}
    />
  </>
);
