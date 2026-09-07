import { AlertItem } from '../types/alert.types';

export interface AlertState {
  alerts: AlertItem[];
  unreadCount: number;
  isSmsFallbackActive: boolean;
  pushNotificationsEnabled: boolean;
}

export const initialAlertState: AlertState = {
  alerts: [],
  unreadCount: 0,
  isSmsFallbackActive: false,
  pushNotificationsEnabled: false,
};
