SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `categoria` INT(5) NOT NULL,
);

INSERT INTO `usuarios` (`nombre`, `email`, `categoria`) VALUES
('Juan Pérez', 'juan.perez@example.com', 1),
('María López', 'maria.lopez@example.com', 2),
('Carlos García', 'carlos.garcia@example.com', 3),
('Ana Martínez', 'ana.martinez@example.com', 4),
('Luis Fernández', 'luis.fernandez@example.com', 1),
('Sofía Rodríguez', 'sofia.rodriguez@example.com', 2);