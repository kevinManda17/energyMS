import { useEffect } from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import Navigation from "./src/navigation";
import { useAuthStore } from "./src/store/auth";
import { useThemeStore } from "./src/store/theme";
import { palette } from "./src/theme/colors";

export default function App() {
  const { ready, bootstrap }         = useAuthStore();
  const { bootstrap: bootstrapTheme } = useThemeStore();

  useEffect(() => {
    bootstrap();
    bootstrapTheme();
  }, [bootstrap, bootstrapTheme]);

  if (!ready) {
    return (
      <View style={{ flex: 1, justifyContent: "center", backgroundColor: palette.navyDeep }}>
        <ActivityIndicator color={palette.blue} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <Navigation />
    </SafeAreaProvider>
  );
}
