     H DFTACTGRP(*NO) ACTGRP(*CALLER)
     H OPTION(*NODEBUGIO)

     D CarRec          DS                  QUALIFIED
     D  CARID                         5P 0
     D  MAKE                         20A
     D  MODEL                        20A
     D  YEAR                          4P 0
     D  COLOR                        10A
     D  PRICE                         9P 2
     D  STATUS                        1A

     D WkCarId         S              5P 0
     D WkMake          S             20A
     D WkModel         S             20A
     D WkStatus        S              1A
     D WkCount         S              5P 0

      /free

       // Fetch active cars by make
       EXEC SQL
         DECLARE CarCursor CURSOR FOR
           SELECT CARID, MAKE, MODEL, STATUS
             FROM CARFILE
            WHERE STATUS = 'A'
            ORDER BY MAKE, MODEL;

       EXEC SQL OPEN CarCursor;

       DOW 1 = 1;
         EXEC SQL
           FETCH CarCursor INTO :WkCarId, :WkMake, :WkModel, :WkStatus;

         IF SQLSTATE = '02000';
           LEAVE;
         ENDIF;

         // Only process cars where make starts with 'T'
         IF %SUBST(WkMake:1:1) = 'T';
           WkCount += 1;
         ENDIF;

      ENDDO;

      /end-free
