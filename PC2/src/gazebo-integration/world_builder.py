# Custom world creation for Gazebo simulation
"""
World builder for Gazebo simulations
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

class WorldBuilder:
    """Build custom Gazebo worlds"""
    
    def __init__(self):
        """Initialize world builder"""
        self.world_root = None
        self.world_element = None
        self.obstacle_count = 0
        logger.info("World builder initialized")
    
    def create_base_world(self, name: str = "drone_world") -> ET.Element:
        """
        Create base world structure
        
        Args:
            name: World name
            
        Returns:
            World XML root element
        """
        # Create root SDF element
        root = ET.Element('sdf', version='1.6')
        
        # Add world with name
        self.world_element = ET.SubElement(root, 'world', name=name)
        
        # Add sun
        include = ET.SubElement(self.world_element, 'include')
        uri = ET.SubElement(include, 'uri')
        uri.text = 'model://sun'
        
        # Add ground plane
        include = ET.SubElement(self.world_element, 'include')
        uri = ET.SubElement(include, 'uri')
        uri.text = 'model://ground_plane'
        
        # Add default lighting
        self._add_lighting()
        
        # Add default physics
        self._add_physics()
        
        self.world_root = root
        logger.info(f"Created base world: {name}")
        return root
    
    def _add_lighting(self):
        """Add lighting to world"""
        if self.world_element is None:
            return
            
        # Add ambient light
        light = ET.SubElement(self.world_element, 'light', name='ambient_light', type='ambient')
        cast_shadows = ET.SubElement(light, 'cast_shadows')
        cast_shadows.text = 'false'
        
        # Add directional light (sun)
        light = ET.SubElement(self.world_element, 'light', name='sun', type='directional')
        direction = ET.SubElement(light, 'direction')
        direction.text = '-0.5 0.5 0.8'
        
        diffuse = ET.SubElement(light, 'diffuse')
        diffuse.text = '0.8 0.8 0.8 1'
        
        specular = ET.SubElement(light, 'specular')
        specular.text = '0.1 0.1 0.1 1'
    
    def _add_physics(self):
        """Add physics configuration"""
        if self.world_element is None:
            return
            
        physics = ET.SubElement(self.world_element, 'physics', name='default_physics', type='ode')
        
        # Gravity
        gravity = ET.SubElement(physics, 'gravity')
        gravity.text = '0 0 -9.81'
        
        # Max step size
        max_step_size = ET.SubElement(physics, 'max_step_size')
        max_step_size.text = '0.001'
        
        # Real time factor
        real_time_factor = ET.SubElement(physics, 'real_time_factor')
        real_time_factor.text = '1.0'
        
        # ODE solver settings
        solver = ET.SubElement(physics, 'solver')
        ode = ET.SubElement(solver, 'ode')
        
        # Contact parameters
        constraints = ET.SubElement(ode, 'constraints')
        cfm = ET.SubElement(constraints, 'cfm')
        cfm.text = '0.0'
        erp = ET.SubElement(constraints, 'erp')
        erp.text = '0.2'
    
    def add_obstacle(self, position: List[float], size: List[float], 
                     color: List[float] = None, name: str = None) -> ET.Element:
        """
        Add obstacle to world
        
        Args:
            position: [x, y, z] position
            size: [width, height, depth] size
            color: [r, g, b] color (0-1)
            name: Optional custom name
            
        Returns:
            Model element
        """
        if self.world_element is None:
            logger.error("No world created. Call create_base_world() first.")
            return None
            
        if color is None:
            color = [0.5, 0.5, 0.5]
        
        if name is None:
            name = f'obstacle_{self.obstacle_count}'
            self.obstacle_count += 1
        
        model = ET.SubElement(self.world_element, 'model', name=name)
        
        # Static obstacle (doesn't move)
        static = ET.SubElement(model, 'static')
        static.text = 'true'
        
        # Set pose
        pose = ET.SubElement(model, 'pose')
        pose.text = f'{position[0]} {position[1]} {position[2]} 0 0 0'
        
        # Add link
        link = ET.SubElement(model, 'link', name='link')
        
        # Add collision geometry
        collision = ET.SubElement(link, 'collision', name='collision')
        geometry = ET.SubElement(collision, 'geometry')
        box = ET.SubElement(geometry, 'box')
        size_elem = ET.SubElement(box, 'size')
        size_elem.text = f'{size[0]} {size[1]} {size[2]}'
        
        # Add visual geometry
        visual = ET.SubElement(link, 'visual', name='visual')
        geometry = ET.SubElement(visual, 'geometry')
        box = ET.SubElement(geometry, 'box')
        size_elem = ET.SubElement(box, 'size')
        size_elem.text = f'{size[0]} {size[1]} {size[2]}'
        
        # Add material with color
        material = ET.SubElement(visual, 'material')
        script = ET.SubElement(material, 'script')
        uri = ET.SubElement(script, 'uri')
        uri.text = 'file://media/materials/scripts/gazebo.material'
        script_name = ET.SubElement(script, 'name')
        
        # Map RGB to Gazebo material name
        material_names = {
            (1, 0, 0): 'Gazebo/Red',
            (0, 1, 0): 'Gazebo/Green', 
            (0, 0, 1): 'Gazebo/Blue',
            (1, 1, 0): 'Gazebo/Yellow',
            (0, 1, 1): 'Gazebo/Cyan',
            (1, 0, 1): 'Gazebo/Magenta',
            (0.5, 0.5, 0.5): 'Gazebo/Grey',
            (0.2, 0.2, 0.2): 'Gazebo/DarkGrey',
            (0.8, 0.8, 0.8): 'Gazebo/LightGrey'
        }
        
        # Find closest color match or use custom
        key = tuple(round(c, 1) for c in color)
        if key in material_names:
            script_name.text = material_names[key]
        else:
            script_name.text = f'Gazebo/Custom'
            # Add custom color via ambient/diffuse
            ambient = ET.SubElement(material, 'ambient')
            ambient.text = f'{color[0]} {color[1]} {color[2]} 1'
            diffuse = ET.SubElement(material, 'diffuse')
            diffuse.text = f'{color[0]} {color[1]} {color[2]} 1'
        
        logger.info(f"Added obstacle '{name}' at position {position} with size {size}")
        return model
    
    def add_sphere_obstacle(self, position: List[float], radius: float, 
                            color: List[float] = None, name: str = None) -> ET.Element:
        """
        Add spherical obstacle to world
        
        Args:
            position: [x, y, z] position
            radius: Sphere radius
            color: [r, g, b] color (0-1)
            name: Optional custom name
            
        Returns:
            Model element
        """
        if self.world_element is None:
            logger.error("No world created. Call create_base_world() first.")
            return None
            
        if color is None:
            color = [0.5, 0.5, 0.5]
        
        if name is None:
            name = f'sphere_obstacle_{self.obstacle_count}'
            self.obstacle_count += 1
        
        model = ET.SubElement(self.world_element, 'model', name=name)
        
        # Static obstacle
        static = ET.SubElement(model, 'static')
        static.text = 'true'
        
        # Set pose
        pose = ET.SubElement(model, 'pose')
        pose.text = f'{position[0]} {position[1]} {position[2]} 0 0 0'
        
        # Add link
        link = ET.SubElement(model, 'link', name='link')
        
        # Add collision geometry
        collision = ET.SubElement(link, 'collision', name='collision')
        geometry = ET.SubElement(collision, 'geometry')
        sphere = ET.SubElement(geometry, 'sphere')
        radius_elem = ET.SubElement(sphere, 'radius')
        radius_elem.text = str(radius)
        
        # Add visual geometry
        visual = ET.SubElement(link, 'visual', name='visual')
        geometry = ET.SubElement(visual, 'geometry')
        sphere = ET.SubElement(geometry, 'sphere')
        radius_elem = ET.SubElement(sphere, 'radius')
        radius_elem.text = str(radius)
        
        # Add material
        material = ET.SubElement(visual, 'material')
        script = ET.SubElement(material, 'script')
        uri = ET.SubElement(script, 'uri')
        uri.text = 'file://media/materials/scripts/gazebo.material'
        script_name = ET.SubElement(script, 'name')
        script_name.text = f'Gazebo/{int(color[0]*255)} {int(color[1]*255)} {int(color[2]*255)}'
        
        logger.info(f"Added sphere obstacle '{name}' at position {position} with radius {radius}")
        return model
    
    def add_cylinder_obstacle(self, position: List[float], radius: float, length: float,
                               color: List[float] = None, name: str = None) -> ET.Element:
        """
        Add cylindrical obstacle to world
        
        Args:
            position: [x, y, z] position
            radius: Cylinder radius
            length: Cylinder length (height)
            color: [r, g, b] color (0-1)
            name: Optional custom name
            
        Returns:
            Model element
        """
        if self.world_element is None:
            logger.error("No world created. Call create_base_world() first.")
            return None
            
        if color is None:
            color = [0.5, 0.5, 0.5]
        
        if name is None:
            name = f'cylinder_obstacle_{self.obstacle_count}'
            self.obstacle_count += 1
        
        model = ET.SubElement(self.world_element, 'model', name=name)
        
        # Static obstacle
        static = ET.SubElement(model, 'static')
        static.text = 'true'
        
        # Set pose
        pose = ET.SubElement(model, 'pose')
        pose.text = f'{position[0]} {position[1]} {position[2]} 0 0 0'
        
        # Add link
        link = ET.SubElement(model, 'link', name='link')
        
        # Add collision geometry
        collision = ET.SubElement(link, 'collision', name='collision')
        geometry = ET.SubElement(collision, 'geometry')
        cylinder = ET.SubElement(geometry, 'cylinder')
        radius_elem = ET.SubElement(cylinder, 'radius')
        radius_elem.text = str(radius)
        length_elem = ET.SubElement(cylinder, 'length')
        length_elem.text = str(length)
        
        # Add visual geometry
        visual = ET.SubElement(link, 'visual', name='visual')
        geometry = ET.SubElement(visual, 'geometry')
        cylinder = ET.SubElement(geometry, 'cylinder')
        radius_elem = ET.SubElement(cylinder, 'radius')
        radius_elem.text = str(radius)
        length_elem = ET.SubElement(cylinder, 'length')
        length_elem.text = str(length)
        
        # Add material
        material = ET.SubElement(visual, 'material')
        ambient = ET.SubElement(material, 'ambient')
        ambient.text = f'{color[0]} {color[1]} {color[2]} 1'
        diffuse = ET.SubElement(material, 'diffuse')
        diffuse.text = f'{color[0]} {color[1]} {color[2]} 1'
        
        logger.info(f"Added cylinder obstacle '{name}' at position {position}")
        return model
    
    def add_waypoints(self, waypoints: List[List[float]], color: List[float] = None):
        """
        Add visual waypoints marker to world
        
        Args:
            waypoints: List of [x, y, z] positions
            color: Marker color [r, g, b]
        """
        if self.world_element is None:
            logger.error("No world created. Call create_base_world() first.")
            return
            
        if color is None:
            color = [1.0, 0.0, 0.0]  # Red
        
        for i, wp in enumerate(waypoints):
            # Create a small sphere at waypoint position
            marker_name = f'waypoint_{i}'
            model = ET.SubElement(self.world_element, 'model', name=marker_name)
            
            static = ET.SubElement(model, 'static')
            static.text = 'true'
            
            pose = ET.SubElement(model, 'pose')
            pose.text = f'{wp[0]} {wp[1]} {wp[2]} 0 0 0'
            
            link = ET.SubElement(model, 'link', name='link')
            
            # Add visual sphere
            visual = ET.SubElement(link, 'visual', name='visual')
            geometry = ET.SubElement(visual, 'geometry')
            sphere = ET.SubElement(geometry, 'sphere')
            radius = ET.SubElement(sphere, 'radius')
            radius.text = '0.2'
            
            # Make it glow
            material = ET.SubElement(visual, 'material')
            ambient = ET.SubElement(material, 'ambient')
            ambient.text = f'{color[0]} {color[1]} {color[2]} 1'
            diffuse = ET.SubElement(material, 'diffuse')
            diffuse.text = f'{color[0]} {color[1]} {color[2]} 1'
            emissive = ET.SubElement(material, 'emissive')
            emissive.text = f'{color[0]*0.5} {color[1]*0.5} {color[2]*0.5} 1'
        
        logger.info(f"Added {len(waypoints)} waypoint markers")
    
    def add_no_fly_zone(self, center: List[float], radius: float, height: float = 10.0):
        """
        Add a no-fly zone visual marker
        
        Args:
            center: [x, y, z] center position
            radius: Zone radius
            height: Zone height (cylinder)
        """
        if self.world_element is None:
            logger.error("No world created. Call create_base_world() first.")
            return
        
        # Add semi-transparent cylinder to mark no-fly zone
        model = ET.SubElement(self.world_element, 'model', name='no_fly_zone')
        
        static = ET.SubElement(model, 'static')
        static.text = 'true'
        
        pose = ET.SubElement(model, 'pose')
        pose.text = f'{center[0]} {center[1]} {center[2] + height/2} 0 0 0'
        
        link = ET.SubElement(model, 'link', name='link')
        
        # Visual cylinder
        visual = ET.SubElement(link, 'visual', name='visual')
        geometry = ET.SubElement(visual, 'geometry')
        cylinder = ET.SubElement(geometry, 'cylinder')
        radius_elem = ET.SubElement(cylinder, 'radius')
        radius_elem.text = str(radius)
        length_elem = ET.SubElement(cylinder, 'length')
        length_elem.text = str(height)
        
        # Red semi-transparent material
        material = ET.SubElement(visual, 'material')
        ambient = ET.SubElement(material, 'ambient')
        ambient.text = '1 0 0 0.3'
        diffuse = ET.SubElement(material, 'diffuse')
        diffuse.text = '1 0 0 0.3'
        transparency = ET.SubElement(material, 'transparency')
        transparency.text = '0.7'
        
        logger.info(f"Added no-fly zone at {center} with radius {radius}")
    
    def save_world(self, filepath: str):
        """
        Save world to file
        
        Args:
            filepath: Output file path
        """
        if self.world_root is None:
            logger.error("No world created. Call create_base_world() first.")
            return
        
        # Create directory if it doesn't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Convert to string and write
        tree = ET.ElementTree(self.world_root)
        
        # Add XML declaration
        with open(filepath, 'wb') as f:
            f.write(b'<?xml version="1.0" ?>\n')
            tree.write(f, encoding='utf-8', xml_declaration=False)
        
        logger.info(f"World saved to {filepath}")
    
    def generate_forest_world(self, filepath: str, num_trees: int = 20, 
                               area_size: float = 50.0):
        """
        Generate a forest world with multiple tree obstacles
        
        Args:
            filepath: Output file path
            num_trees: Number of trees to generate
            area_size: Size of the forest area (-area_size/2 to area_size/2)
        """
        import random
        
        self.create_base_world("forest_world")
        
        # Add trees as cylinder obstacles
        for i in range(num_trees):
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            z = 0  # Ground level
            
            radius = random.uniform(0.3, 0.6)
            height = random.uniform(2.0, 4.0)
            
            # Brown trunk
            self.add_cylinder_obstacle(
                position=[x, y, z],
                radius=radius,
                length=height,
                color=[0.55, 0.27, 0.07],
                name=f'tree_trunk_{i}'
            )
            
            # Green canopy on top
            self.add_sphere_obstacle(
                position=[x, y, z + height],
                radius=radius * 1.5,
                color=[0.0, 0.5, 0.0],
                name=f'tree_canopy_{i}'
            )
        
        self.save_world(filepath)
        logger.info(f"Forest world generated with {num_trees} trees at {filepath}")
    
    def generate_urban_world(self, filepath: str, num_buildings: int = 15,
                              grid_size: float = 100.0):
        """
        Generate an urban world with building obstacles
        
        Args:
            filepath: Output file path
            num_buildings: Number of buildings to generate
            grid_size: Size of the urban area
        """
        import random
        
        self.create_base_world("urban_world")
        
        for i in range(num_buildings):
            x = random.uniform(-grid_size/2, grid_size/2)
            y = random.uniform(-grid_size/2, grid_size/2)
            
            # Avoid center (drone takeoff area)
            if abs(x) < 10 and abs(y) < 10:
                continue
            
            width = random.uniform(3.0, 8.0)
            depth = random.uniform(3.0, 8.0)
            height = random.uniform(5.0, 20.0)
            
            # Random building colors
            colors = [
                [0.7, 0.7, 0.7],  # Grey
                [0.8, 0.6, 0.4],  # Brown
                [0.9, 0.9, 0.8],  # Light grey
                [0.5, 0.5, 0.5]   # Dark grey
            ]
            color = random.choice(colors)
            
            self.add_obstacle(
                position=[x, y, 0],
                size=[width, height, depth],
                color=color,
                name=f'building_{i}'
            )
        
        self.save_world(filepath)
        logger.info(f"Urban world generated with {num_buildings} buildings at {filepath}")
    
    def get_world_xml_string(self) -> str:
        """
        Get world as XML string
        
        Returns:
            World XML as string
        """
        if self.world_root is None:
            return ""
        
        # Convert to string
        xml_str = ET.tostring(self.world_root, encoding='unicode')
        return f'<?xml version="1.0" ?>\n{xml_str}'


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Create a simple world with obstacles
    builder = WorldBuilder()
    builder.create_base_world("test_world")
    
    # Add some obstacles
    builder.add_obstacle(position=[5, 5, 0], size=[2, 3, 2], color=[1, 0, 0], name="red_box")
    builder.add_obstacle(position=[-5, 5, 0], size=[2, 2, 2], color=[0, 1, 0], name="green_box")
    builder.add_sphere_obstacle(position=[0, 10, 1], radius=1.0, color=[0, 0, 1], name="blue_sphere")
    builder.add_cylinder_obstacle(position=[10, 0, 0], radius=1.0, length=3.0, color=[1, 1, 0])
    
    # Add waypoints
    builder.add_waypoints([[0, 0, 2], [5, 5, 5], [-5, 5, 5], [0, 10, 3]])
    
    # Add no-fly zone
    builder.add_no_fly_zone(center=[0, 0, 0], radius=8.0, height=15.0)
    
    # Save world
    builder.save_world("/tmp/test_world.world")
    
    # Example 2: Generate a forest world
    builder2 = WorldBuilder()
    builder2.generate_forest_world("/tmp/forest_world.world", num_trees=30)
    
    # Example 3: Generate an urban world
    builder3 = WorldBuilder()
    builder3.generate_urban_world("/tmp/urban_world.world", num_buildings=20)
    
    print("World files generated in /tmp/")
    print("- /tmp/test_world.world")
    print("- /tmp/forest_world.world")
    print("- /tmp/urban_world.world")