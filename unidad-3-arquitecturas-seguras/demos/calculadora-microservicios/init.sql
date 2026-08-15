SET NAMES utf8mb4;

CREATE TABLE operaciones (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    tipo       VARCHAR(20) NOT NULL,
    operando_a DOUBLE,
    operando_b DOUBLE,
    resultado  DOUBLE NOT NULL,
    expresion  VARCHAR(50),
    creado_en  DATETIME NOT NULL
);