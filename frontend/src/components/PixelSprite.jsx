import { PixelSpriteAsset } from "../assets/pixelSprites.jsx";

export default function PixelSprite({ type, skin, label, variant }) {
  return <PixelSpriteAsset type={type} skin={skin} label={label || skin || variant || type} variant={variant} />;
}
