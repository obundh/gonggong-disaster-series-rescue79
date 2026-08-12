"""Temporal skeleton classifier used by the portable Rescue79 checkpoint."""

from __future__ import annotations

import torch
from torch import nn


class ResidualTemporalBlock(nn.Module):
    """A residual temporal convolution block preserved from the training code."""

    def __init__(self, channels: int, dropout: float, dilation: int) -> None:
        super().__init__()
        padding = dilation * 2
        self.net = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size=5, padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size=5, padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
        )
        self.activation = nn.GELU()

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.activation(value + self.net(value))


class TemporalConvClassifier(nn.Module):
    """Classify a [batch, time, joint, feature] skeleton tensor."""

    def __init__(
        self,
        num_joints: int,
        features_per_joint: int,
        num_classes: int,
        hidden_channels: int = 64,
        dropout: float = 0.1,
        dilations: tuple[int, ...] = (1, 2, 4),
    ) -> None:
        super().__init__()
        if not dilations or any(int(value) <= 0 for value in dilations):
            raise ValueError("dilations must contain positive integers")
        self.num_joints = num_joints
        self.features_per_joint = features_per_joint
        self.dilations = tuple(int(value) for value in dilations)
        self.input_projection = nn.Linear(
            num_joints * features_per_joint, hidden_channels
        )
        self.temporal = nn.Sequential(
            *(
                ResidualTemporalBlock(hidden_channels, dropout, dilation=dilation)
                for dilation in self.dilations
            )
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.classifier = nn.Linear(hidden_channels, num_classes)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        if value.ndim != 4:
            raise ValueError(f"Expected [B,T,J,F], got {tuple(value.shape)}")
        if (
            value.shape[2] != self.num_joints
            or value.shape[3] != self.features_per_joint
        ):
            raise ValueError(
                "Expected J,F="
                f"{self.num_joints},{self.features_per_joint}; got {value.shape[2:]}"
            )
        value = value.flatten(start_dim=2)
        value = self.input_projection(value)
        value = value.transpose(1, 2)
        value = self.temporal(value)
        value = self.pool(value).squeeze(-1)
        return self.classifier(value)
