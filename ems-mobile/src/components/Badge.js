import { View, Text } from "react-native";
import { palette } from "../theme/colors";

const VARIANTS = {
  CRITICAL:        { bg: palette.dangerLight,  text: palette.danger,   border: "#FCA5A5" },
  WARNING:         { bg: palette.solarLight,   text: "#B45309",        border: "#FCD34D" },
  INFO:            { bg: palette.blueLight,    text: palette.blue,     border: "#93C5FD" },
  NONE:            { bg: "#F1F5F9",            text: palette.slate,    border: palette.border },
  VALID:           { bg: palette.greenLight,   text: palette.green,    border: "#86EFAC" },
  ACTIVE:          { bg: palette.greenLight,   text: palette.green,    border: "#86EFAC" },
  ONLINE:          { bg: palette.greenLight,   text: palette.green,    border: "#86EFAC" },
  INACTIVE:        { bg: "#F1F5F9",            text: palette.slate,    border: palette.border },
  OFFLINE:         { bg: palette.dangerLight,  text: palette.danger,   border: "#FCA5A5" },
  FAULT:           { bg: palette.dangerLight,  text: palette.danger,   border: "#FCA5A5" },
  SHEDDED:         { bg: palette.solarLight,   text: "#B45309",        border: "#FCD34D" },
  AUTOMATIC:       { bg: palette.greenLight,   text: palette.green,    border: "#86EFAC" },
  RECOMMENDATION:  { bg: palette.solarLight,   text: "#B45309",        border: "#FCD34D" },
  BLOCKED:         { bg: palette.dangerLight,  text: palette.danger,   border: "#FCA5A5" },
  NORMAL:          { bg: palette.blueLight,    text: palette.blue,     border: "#93C5FD" },
  HIGH:            { bg: palette.solarLight,   text: "#B45309",        border: "#FCD34D" },
  LOW:             { bg: "#F1F5F9",            text: palette.slate,    border: palette.border },
};

const DEFAULT_VARIANT = { bg: "#F1F5F9", text: palette.slate, border: palette.border };

export function Badge({ value }) {
  const v = VARIANTS[value] || DEFAULT_VARIANT;
  return (
    <View
      style={{
        backgroundColor: v.bg,
        borderWidth: 1,
        borderColor: v.border,
        paddingHorizontal: 9,
        paddingVertical: 3,
        borderRadius: 999,
        alignSelf: "flex-start",
      }}
    >
      <Text style={{ color: v.text, fontSize: 11, fontWeight: "700", letterSpacing: 0.3 }}>
        {value}
      </Text>
    </View>
  );
}
