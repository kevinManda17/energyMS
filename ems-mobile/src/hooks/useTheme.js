import { useColorScheme } from "react-native";
import { themes } from "../theme/colors";

/** Returns the active theme object based on the OS color scheme. */
export function useTheme() {
  const scheme = useColorScheme();
  return themes[scheme === "dark" ? "dark" : "light"];
}
