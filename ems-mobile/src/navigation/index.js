import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useColorScheme } from "react-native";
import { Activity, ChartNetwork, CirclePlus, GitBranch, HousePlug } from "lucide-react-native";

import { useAuthStore } from "../store/auth";
import { palette } from "../theme/colors";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import DashboardScreen from "../screens/DashboardScreen";
import HousesScreen from "../screens/HousesScreen";
import HistoryScreen from "../screens/HistoryScreen";
import DecisionsScreen from "../screens/DecisionsScreen";
import AlertsScreen from "../screens/AlertsScreen";
import SettingsScreen from "../screens/SettingsScreen";
import DecisionDetailScreen from "../screens/DecisionDetailScreen";
import AlertDetailScreen from "../screens/AlertDetailScreen";
import DevicesScreen from "../screens/DevicesScreen";
import ForecastingScreen from "../screens/ForecastingScreen";
import ReportsScreen from "../screens/ReportsScreen";
import PricingScreen from "../screens/PricingScreen";
import MoreScreen from "../screens/MoreScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: palette.blue,
        tabBarInactiveTintColor: "#8A8F98",
        tabBarLabelStyle: { fontWeight: "700" },
        tabBarIcon: ({ color, size }) => {
          const icons = {
            Accueil: HousePlug,
            Reseaux: ChartNetwork,
            Mesures: Activity,
            Decisions: GitBranch,
            Plus: CirclePlus,
          };
          const Icon = icons[route.name] || CirclePlus;
          return <Icon color={color} size={size || 22} strokeWidth={2.4} />;
        },
      })}
    >
      <Tab.Screen name="Accueil" component={DashboardScreen} />
      <Tab.Screen name="Reseaux" component={HousesScreen} />
      <Tab.Screen name="Mesures" component={HistoryScreen} />
      <Tab.Screen name="Decisions" component={DecisionsScreen} />
      <Tab.Screen name="Plus" component={MoreScreen} />
    </Tab.Navigator>
  );
}

export default function Navigation() {
  const scheme = useColorScheme();
  const { isAuthenticated } = useAuthStore();

  return (
    <NavigationContainer theme={scheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack.Navigator>
        {isAuthenticated ? (
          <>
            <Stack.Screen name="Main" component={Tabs} options={{ headerShown: false }} />
            <Stack.Screen name="DecisionDetail" component={DecisionDetailScreen} options={{ title: "Decision" }} />
            <Stack.Screen name="AlertDetail" component={AlertDetailScreen} options={{ title: "Alerte" }} />
            <Stack.Screen name="Devices" component={DevicesScreen} options={{ title: "Equipements" }} />
            <Stack.Screen name="Forecasting" component={ForecastingScreen} options={{ title: "Previsions horaires" }} />
            <Stack.Screen name="Reports" component={ReportsScreen} options={{ title: "Rapports" }} />
            <Stack.Screen name="Pricing" component={PricingScreen} options={{ title: "Tarifs" }} />
            <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Parametres" }} />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegisterScreen} options={{ headerShown: false }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
