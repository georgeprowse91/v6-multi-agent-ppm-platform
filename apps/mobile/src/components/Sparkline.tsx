import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, Line, Polyline } from 'react-native-svg';

import { colors } from '../theme';

type SparklineProps = {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showDot?: boolean;
  strokeWidth?: number;
};

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 80,
  height = 24,
  color = colors.accent,
  showDot = true,
  strokeWidth = 1.5,
}) => {
  if (data.length < 2) {
    return <View style={{ width, height }} />;
  }

  const padding = 2;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((value, index) => {
      const x = padding + (index / (data.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((value - min) / range) * chartHeight;
      return `${x},${y}`;
    })
    .join(' ');

  const lastX = padding + ((data.length - 1) / (data.length - 1)) * chartWidth;
  const lastY = padding + chartHeight - ((data[data.length - 1] - min) / range) * chartHeight;

  return (
    <View style={{ width, height }}>
      <Svg width={width} height={height}>
        <Polyline points={points} fill="none" stroke={color} strokeWidth={strokeWidth} />
        {showDot && <Circle cx={lastX} cy={lastY} r={2} fill={color} />}
      </Svg>
    </View>
  );
};

type HealthBadgeBarProps = {
  score: number;
  width?: number;
  height?: number;
};

export const HealthBadgeBar: React.FC<HealthBadgeBarProps> = ({
  score,
  width = 60,
  height = 6,
}) => {
  const clampedScore = Math.max(0, Math.min(1, score));
  const fillWidth = clampedScore * width;

  let barColor = colors.success;
  if (clampedScore < 0.4) {
    barColor = colors.danger;
  } else if (clampedScore < 0.7) {
    barColor = colors.warning;
  }

  return (
    <View style={{ width, height }}>
      <Svg width={width} height={height}>
        <Line
          x1={0}
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={height}
          strokeLinecap="round"
        />
        <Line
          x1={0}
          y1={height / 2}
          x2={fillWidth}
          y2={height / 2}
          stroke={barColor}
          strokeWidth={height}
          strokeLinecap="round"
        />
      </Svg>
    </View>
  );
};
