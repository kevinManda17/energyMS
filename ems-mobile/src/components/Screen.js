import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../hooks/useTheme";

export function Screen({ children, style }) {
  const t = useTheme();
  return (
    <SafeAreaView edges={["top", "left", "right"]} style={[styles.safe, { backgroundColor: t.bg }]}>
      <View style={[styles.content, style]}>{children}</View>
    </SafeAreaView>
  );
}

export function ScreenScroll({ children, style, contentContainerStyle, ...props }) {
  const t = useTheme();
  return (
    <SafeAreaView edges={["top", "left", "right"]} style={[styles.safe, { backgroundColor: t.bg }]}>
      <ScrollView
        style={[{ backgroundColor: t.bg }, style]}
        contentContainerStyle={[styles.scrollContent, contentContainerStyle]}
        {...props}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function PageTitle({ title, subtitle }) {
  const t = useTheme();
  return (
    <View style={styles.header}>
      <Text style={[styles.title, { color: t.text }]}>{title}</Text>
      {subtitle ? <Text style={[styles.subtitle, { color: t.sub }]}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  content: { flex: 1, paddingHorizontal: 16, paddingTop: 10 },
  scrollContent: { paddingHorizontal: 16, paddingTop: 10, paddingBottom: 28 },
  header: { marginBottom: 16 },
  title: { fontSize: 28, fontWeight: "800", lineHeight: 34 },
  subtitle: { marginTop: 4, fontSize: 14 },
});
