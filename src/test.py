import numpy as np
import matplotlib.pyplot as plt

# Generate angle data
# Theta for vertical plane (from -pi/2 to pi/2 to show both sides of the z-axis)
theta = np.linspace(-np.pi/2, np.pi/2, 500)
# Phi for horizontal plane (0 to 2*pi)
phi = np.linspace(0, 2*np.pi, 500)

# Calculate radiation patterns
# For the vertical plane, the pattern is cos^3(theta)
r_vertical = np.cos(theta)**3
# Ensure we don't plot negative values caused by floating point inaccuracies at pi/2
r_vertical = np.clip(r_vertical, 0, None)

# For the horizontal azimuthal pattern, it is rotationally symmetric (constant for all phi).
# We plot a normalized circle to represent the omnidirectional phi-independence.
r_horizontal = np.ones_like(phi)

# Create the figure
fig = plt.figure(figsize=(12, 6))

# --- Plot 1: Vertical Plane (x/z) ---
ax1 = fig.add_subplot(121, projection='polar')
ax1.plot(theta, r_vertical, color='blue', linewidth=2)
# Set zero degrees (theta=0) to point UP (representing the Z-axis)
ax1.set_theta_zero_location("N")
# Make theta increase clockwise (standard representation for elevation angles)
ax1.set_theta_direction(-1)
# Restrict the plot to the upper hemisphere (Z >= 0)
ax1.set_thetamin(-90)
ax1.set_thetamax(90)
ax1.set_title("Vertikales Richtdiagramm (x/z-Ebene)\nLobe points up along Z-axis", va='bottom', pad=20)
# Custom tick labels for axes
ax1.set_xticks(np.radians([-90, -45, 0, 45, 90]))
ax1.set_xticklabels(['-X', '', 'Z', '', 'X'])

# --- Plot 2: Horizontal Plane (x/y) ---
ax2 = fig.add_subplot(122, projection='polar')
ax2.plot(phi, r_horizontal, color='red', linewidth=2)
ax2.set_title("Horizontales Richtdiagramm (x/y-Ebene)\nAzimuthal Symmetry (Omnidirectional)", va='bottom', pad=20)
ax2.set_rticks([0.5, 1])  # Less radial ticks
ax2.set_xticks(np.radians([0, 90, 180, 270]))
ax2.set_xticklabels(['X', 'Y', '-X', '-Y'])

plt.tight_layout()
plt.show()