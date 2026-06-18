import { View, Text } from "react-native";
import { palette } from "../theme/colors";

const COLORS = {
  CRITICAL: palette.danger,
  WARNING: palette.solar,
  INFO: palette.blue,
  NONE: palette.slate,
  VALID: palette.green,
  ACTIVE: palette.green,
  INACTIVE: palette.slate,
  FAULT: palette.danger,
  SHEDDED: palette.solar,
  AUTOMATIC: palette.green,
  RECOMMENDATION: palette.solar,
  BLOCKED: palette.danger,
};

export function Badge({ value }) {
  const color = COLORS[value] || palette.slate;
  return (
    <View
      style={{
        backgroundColor: color + "22",
        paddingHorizontal: 10,
        paddingVertical: 3,
        borderRadius: 999,
        alignSelf: "flex-start",
      }}
    >
      <Text style={{ color, fontSize: 11, fontWeight: "600" }}>{value}</Text>
    </View>
  );
}
