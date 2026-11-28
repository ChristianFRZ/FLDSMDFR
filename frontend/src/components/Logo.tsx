import horizontalDark from "../assets/meloxo-horizontal-color-dark.svg";
import horizontalLight from "../assets/meloxo-horizontal-color-light.svg";
import stackedDark from "../assets/meloxo-stacked-color-dark.svg";
import stackedLight from "../assets/meloxo-stacked-color-light.svg";
import { useTheme } from "../theme";

const logos = {
  horizontal: { dark: horizontalDark, light: horizontalLight },
  stacked: { dark: stackedDark, light: stackedLight },
};

/** El logo que se lee sobre el fondo del tema: el de "dark" es para fondos oscuros, el de "light" para claros. */
export function Logo({ variant, alt, className }: { variant: keyof typeof logos; alt: string; className?: string }) {
  const { resolved } = useTheme();
  return <img className={className} src={logos[variant][resolved]} alt={alt} />;
}
