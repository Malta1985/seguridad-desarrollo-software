SET NAMES utf8mb4;

CREATE TABLE usuarios (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL
);

CREATE TABLE libros (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    titulo     VARCHAR(200) NOT NULL,
    autor      VARCHAR(150) NOT NULL,
    anio       INT,
    disponible TINYINT NOT NULL DEFAULT 1
);

INSERT INTO usuarios (username, password) VALUES
    ('admin', '$2b$12$caY9f4QJfjxYtCbiF5twf.qVj/Y8OXQ8RMl1yJbQ70FIupqwUKOeq'),
    ('maria.rodriguez', '$2b$12$ab9gHKnVL/980zlXxDq36eEOzOBJ9c/Koh6ArBjKkzC4MK6m/m7vG'),
    ('bibliotecario', '$2b$12$shn/vAt/WV6V1eAb2Sc0COO4TVCcs/60qewuJiDGwLs9sqJmHOlVW');

INSERT INTO libros (titulo, autor, anio, disponible) VALUES
    ('Cien años de soledad', 'Gabriel García Márquez', 1967, 1),
    ('El amor en los tiempos del cólera', 'Gabriel García Márquez', 1985, 1),
    ('Don Quijote de la Mancha', 'Miguel de Cervantes', 1605, 0),
    ('La vorágine', 'José Eustasio Rivera', 1924, 1),
    ('Rayuela', 'Julio Cortázar', 1963, 1),
    ('Pedro Páramo', 'Juan Rulfo', 1955, 1),
    ('La ciudad y los perros', 'Mario Vargas Llosa', 1963, 0),
    ('Ficciones', 'Jorge Luis Borges', 1944, 1);
